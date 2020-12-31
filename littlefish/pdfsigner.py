"""
This module uses endesive to sign PDF files and provides
some classes to manage this and to help render the signature
into the body of the PDF file (similar for portable signer)
"""

import logging
import datetime

import OpenSSL.crypto
import endesive.pdf
import pytz

__author__ = 'Stephen Brown (Little Fish Solutions LTD)'

log = logging.getLogger(__name__)


class Signature:
    """
    Represents a signature on a PDF
    """
    def __init__(self, contact, issuer, serial_number, location, reason, flags=3,
                 timezone='Europe/London'):
        """
        :param contact: The person signing the PDF eg 'Bob the Builder'
        :param issuer: The certificate issuer eg
                       'C=GB, ST=Greater Manchester, L=Salford, O=Sectigo Limited,
                        CN=Sectigo RSA Client Authentication and Secure Email CA'
        :param serial_number: Certificate serial number
        :param location: Location of signing eg 'Some Place, Acton, London'
        :param reason: Why are you signing this? eg 'Customer Contract'
        :param flags: I have no idea what this is but it works if you set it to 3!
        :param timezone: You can override the timezone with this
        """
        self.flags = flags
        self.contact = contact
        self.issuer = issuer
        self.serial_number = serial_number
        self.location = location
        self.signing_date = datetime.datetime.utcnow()
        self.reason = reason

        local_timezone = pytz.timezone(timezone)
        self.timezone = local_timezone.tzname(self.signing_date)

    def get_signature_args(self):
        """
        Get the arguments in the weird format needed for signing
        """
        timestamp = self.signing_date.strftime('%Y%m%d%H%M%S+00\'00\'')

        return {
            'sigflags': 3,
            'contact': self.contact.encode(),
            'location': self.location.encode(),
            'signingdate': timestamp.encode(),
            'reason': self.reason.encode()
        }


class Signer:
    """
    A Signer object is used to sign PDF files.  Create one and use it to sign stuff!

    Create a Signer, then pass in Signer.signature to your PDF generator if you want
    to render the signature.  Then get the PDF file (bytes) and pass it into
    get_signed_pdf(...) to sign it.
    """
    def __init__(self, pfx_path, password, location, reason):
        """
        :param pfx_path: Full path to the PFX file with the certificate
        :param password: Plain password used to decrypt the PFX file
        :param location: Where are you signing from i.e. "Steve's House, Cambridge"
        :param reason: Why are you signing i.e. "Fake University Degree Certificate"
        """
        log.debug('Loading PFX file: "{}"'.format(pfx_path))

        with open(pfx_path, 'rb') as cert_file:
            pfx = OpenSSL.crypto.load_pkcs12(cert_file.read(), password)
        
        self.private_key = pfx.get_privatekey().to_cryptography_key()
        cert = pfx.get_certificate()
        self.cert = cert.to_cryptography()

        name_parts = ['{}={}'.format(name.decode(), value.decode()) for name, value in cert.get_subject().get_components()]
        contact = ', '.join(name_parts)
        
        issuer_parts = ['{}={}'.format(name.decode(), value.decode()) for name, value in cert.get_issuer().get_components()]
        issuer = ', '.join(issuer_parts)

        serial_number = cert.get_serial_number()

        self.signature = Signature(
            contact=contact,
            issuer=issuer,
            serial_number=serial_number,
            location=location,
            reason=reason
        )

    def get_pdf_signature(self, unsigned_pdf):
        """
        :param unsigned_pdf: PDF data (bytes)
        :return: Signature to append to PDF (bytes)
        """
        return endesive.pdf.cms.sign(
            unsigned_pdf, self.signature.get_signature_args(), self.private_key, self.cert, [], 'sha256'
        )

    def get_signed_pdf(self, unsigned_pdf):
        """
        :param unsigned_pdf: PDF data (bytes)
        :return: PDF file with signature attached
        """
        return unsigned_pdf + self.get_pdf_signature(unsigned_pdf)
