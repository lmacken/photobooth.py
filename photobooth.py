#!/usr/bin/python
# photobooth.py - version 0.3
# Requires: python-imaging, qrencode, gphoto2, surl
# Author: Luke Macken <lmacken@redhat.com>
# License: GPLv3

import os
import surl
import Image
import subprocess

from uuid import uuid4
from os.path import join, basename, expanduser

# Where to spit out our qrcode, watermarked image, and local html
out = expanduser('~/Desktop/sxsw')

# The watermark to apply to all images
watermark_img = expanduser('~/Desktop/fedora.png')

# This assumes ssh-agent is running so we can do password-less scp
ssh_image_repo = 'fedorapeople.org:~/public_html/sxsw/'

# The public HTTP repository for uploaded images
http_image_repo = 'http://lmacken.fedorapeople.org/sxsw/'

# Size of the qrcode pixels
qrcode_size = 10

# Whether or not to delete the photo after uploading it to the remote server
delete_after_upload = True

# The camera configuration
# Use gphoto2 --list-config and --get-config for more information
gphoto_config = {
    '/main/imgsettings/imagesize': 3, # small
    '/main/imgsettings/imagequality': 0, # normal
    '/main/capturesettings/zoom': 70, # zoom factor
}

# The URL shortener to use
shortener = 'tinyurl.com'

class PhotoBooth(object):

    def initialize(self):
        """ Detect the camera and set the various settings """
        cfg = ['--set-config=%s=%s' % (k, v) for k, v in gphoto_config.items()]
        subprocess.call('gphoto2 --auto-detect ' +
                        ' '.join(cfg), shell=True)

    def capture_photo(self):
        """ Capture a photo and download it from the camera """
        filename = join(out, '%s.jpg' % str(uuid4()))
        cfg = ['--set-config=%s=%s' % (k, v) for k, v in gphoto_config.items()]
        subprocess.call('gphoto2 ' +
                        '--capture-image-and-download ' +
                        '--filename="%s" ' % filename,
                        shell=True)
        return filename

    def process_image(self, filename):
        print "Processing %s..." % filename
        print "Applying watermark..."
        image = self.watermark(filename)
        print "Uploading to remote server..."
        url = self.upload(image)
        print "Generating QRCode..."
        qrcode = self.qrencode(url)
        print "Shortening URL..."
        tiny = self.shorten(url)
        print "Generating HTML..."
        html = self.html_output(url, qrcode, tiny)
        subprocess.call('xdg-open "%s"' % html, shell=True)
        print "Done!"

    def watermark(self, image):
        """ Apply a watermark to an image """
        mark = Image.open(watermark_img)
        im = Image.open(image)
        if im.mode != 'RGBA':
            im = im.convert('RGBA')
        layer = Image.new('RGBA', im.size, (0,0,0,0))
        position = (im.size[0] - mark.size[0], im.size[1] - mark.size[1])
        layer.paste(mark, position)
        outfile = join(out, basename(image))
        Image.composite(layer, im, layer).save(outfile)
        return outfile

    def upload(self, image):
        """ Upload this image to a remote server """
        subprocess.call('scp "%s" %s' % (image, ssh_image_repo), shell=True)
        if delete_after_upload:
            os.unlink(image)
        return http_image_repo + basename(image)

    def qrencode(self, url):
        """ Generate a QRCode for a given URL """
        qrcode = join(out, 'qrcode.png')
        subprocess.call('qrencode -s %d -o "%s" %s' % (
            qrcode_size, qrcode, url), shell=True)
        return qrcode

    def shorten(self, url):
        """ Generate a shortened URL """
        return surl.services.supportedServices()[shortener].get({}, url)

    def html_output(self, image, qrcode, tinyurl):
        """ Output HTML with the image, qrcode, and tinyurl """
        html = """
            <html>
              <center>
                <table>
                  <tr>
                    <td colspan="2">
                        <b><a href="%(tinyurl)s">%(tinyurl)s</a></b>
                    </td>
                  </tr>
                  <tr>
                    <td><img src="%(image)s" border="0"/></td>
                    <td><img src="%(qrcode)s" border="0"/></td>
                  </tr>
                </table>
              </center>
          </html>
        """ % {'image': image, 'qrcode': qrcode, 'tinyurl': tinyurl}
        outfile = join(out, basename(image) + '.html')
        output = file(outfile, 'w')
        output.write(html)
        output.close()
        return outfile

if __name__ == "__main__":
    photobooth = PhotoBooth()
    try:
        photobooth.initialize()
        while True:
            raw_input("Press enter to capture photo.")
            filename = photobooth.capture_photo()
            photobooth.process_image(filename)
    except KeyboardInterrupt:
        print "\nExiting..."
