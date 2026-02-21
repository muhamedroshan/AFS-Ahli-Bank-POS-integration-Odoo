import requests
from collections import defaultdict
import xml.etree.ElementTree as ET
import pprint


class PaymentConnectAFS:
    def __init__(self, service_url, tid, mid, secure_key):
        self.service_url = service_url
        self.tid = tid
        self.mid = mid
        self.secure_key = secure_key

    def log_console(self, message):
        print(f"PaymentConnectAFS Log: {message}")
        print(f"TID: {self.tid}, MID: {self.mid}")
        print(f"Service URL: {self.service_url}")
        print(f"Secure Key: {self.secure_key}")

    @staticmethod
    def _etree_to_dict(t):
        """
        Recursively converts an ElementTree element into a dictionary, stripping namespaces.
        """
        tag = t.tag.split('}')[-1]
        d = {tag: {} if t.attrib else None}
        children = list(t)
        if children:
            dd = defaultdict(list)
            for dc in map(PaymentConnectAFS._etree_to_dict, children):
                for k, v in dc.items():
                    dd[k].append(v)
            d = {tag: {k: v[0] if len(v) == 1 else v for k, v in dd.items()}}
        if t.attrib:
            d[tag].update(('@' + k, v) for k, v in t.attrib.items())
        if t.text and t.text.strip():
            text = t.text.strip()
            if children or t.attrib:
                if d[tag] is None:
                    d[tag] = {}
                d[tag]['#text'] = text
            else:
                d[tag] = text
        elif not children and not t.attrib:
            d[tag] = ''  # Handle empty elements
        return d

    @staticmethod
    def _parse_specific_response(xml_string, result_tag_name):
        """
        Generic parser that looks for a specific result tag within a SOAP response.
        """
        try:
            root = ET.fromstring(xml_string)
            result_element = None
            # Iterate through the entire XML tree to find the element with the specified tag name
            for elem in root.iter():
                if elem.tag.split('}')[-1] == result_tag_name:
                    result_element = elem
                    break

            if result_element is not None:
                parsed_data = PaymentConnectAFS._etree_to_dict(result_element)
                # Extract the dictionary from the root tag
                return parsed_data.get(result_tag_name, parsed_data)
            else:
                # Fallback for simple responses that might not have a 'Result' wrapper
                body_element = next((elem for elem in root.iter() if elem.tag.endswith('Body')), None)
                if body_element is not None and len(list(body_element)) > 0:
                    response_wrapper = body_element[0]
                    # If the wrapper has a result, use it
                    if len(list(response_wrapper)) > 0 and 'Result' in response_wrapper[0].tag:
                         result_element = response_wrapper[0]
                         parsed_data = PaymentConnectAFS._etree_to_dict(result_element)
                         return parsed_data.get(result_element.tag.split('}')[-1], parsed_data)
                    else: # Otherwise, use the wrapper itself
                        parsed_data = PaymentConnectAFS._etree_to_dict(response_wrapper)
                        return parsed_data.get(response_wrapper.tag.split('}')[-1], parsed_data)

                return {"Status": "Error", "Message": f"Could not find '{result_tag_name}' or a valid response body in the XML."}

        except ET.ParseError as e:
            return {"Status": "Error", "Message": f"XML Parse Error: {e}"}
        except Exception as e:
            return {"Status": "Error", "Message": str(e)}

    def _process_response(self, response, result_tag_name):
        """
        Handles the parsing of the HTTP response and returns a dictionary.
        """
        if response.status_code == 200:
            return self._parse_specific_response(response.text, result_tag_name)
        else:
            return {
                "Status": "Error",
                "Message": f"HTTP Error: {response.status_code}",
                "Response": response.text
            }


    def send_apex_sale(
            self,
            amount: float,
            invoice_number: str,
    ):
        service_url = self.service_url
        secure_key = self.secure_key
        tid = self.tid
        mid = self.mid

        ns_data = "http://schemas.datacontract.org/2004/07/"
        inner_payload = f"""
          <tem:webReq xmlns:a="{ns_data}">
            <a:Config>
                <a:EcrCurrencyCode>512</a:EcrCurrencyCode>
                <a:EcrTillerFullName>Python</a:EcrTillerFullName>
                <a:EcrTillerUserName>flan</a:EcrTillerUserName>
                <a:MerchantSecureKey>{secure_key}</a:MerchantSecureKey>
                <a:Mid>{mid}</a:Mid>
                <a:Tid>{tid}</a:Tid>
            </a:Config>
            <a:EcrAmount>{amount}</a:EcrAmount>
            <a:InvoiceNumber>{invoice_number}</a:InvoiceNumber> 
            <a:PanEncrypted></a:PanEncrypted>
            <a:Printer>
                <a:EnablePrintPosReceipt>1</a:EnablePrintPosReceipt> 
                <a:EnablePrintReceiptNote>1</a:EnablePrintReceiptNote>
                <a:InvoiceNumber>{invoice_number}</a:InvoiceNumber>
                <a:PrinterWidth>40</a:PrinterWidth>
                <a:ReceiptNote></a:ReceiptNote>
                <a:ReferenceNumber>{invoice_number}</a:ReferenceNumber>
            </a:Printer>
            <a:TransactionType>SALE</a:TransactionType>
            <a:AuthCode></a:AuthCode>
          </tem:webReq>
        """
        envelope = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/">
       <soapenv:Header/>
       <soapenv:Body>
          <tem:Sale>
             {inner_payload}
          </tem:Sale>
       </soapenv:Body>
    </soapenv:Envelope>"""
        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': 'http://tempuri.org/IEcrComInterface/Sale'
        }
        try:
            response = requests.post(service_url, data=envelope, headers=headers, timeout=45, verify=True)
            return self._process_response(response, 'SaleResult')
        except Exception as e:
            print(f"Network Error: {e}")

    def send_apex_enquiry(
            self,
            reference_number: str
    ):
        """
        Checks the status of a previous transaction using the ECR-generated reference number.
        This corresponds to the 'EnquiryByRef' operation.
        """
        service_url = self.service_url
        secure_key = self.secure_key
        tid = self.tid
        mid = self.mid
        ns_data = "http://schemas.datacontract.org/2004/07/"

        inner_payload = f"""
          <tem:webReq xmlns:a="{ns_data}">
            <a:Config>
                <a:EcrCurrencyCode>512</a:EcrCurrencyCode>
                <a:EcrTillerFullName>Python</a:EcrTillerFullName>
                <a:EcrTillerUserName>flan</a:EcrTillerUserName>
                <a:MerchantSecureKey>{secure_key}</a:MerchantSecureKey>
                <a:Mid>{mid}</a:Mid>
                <a:Tid>{tid}</a:Tid>
            </a:Config>
            <a:Printer>
                <a:ReferenceNumber>{reference_number}</a:ReferenceNumber>
            </a:Printer>
          </tem:webReq>
        """

        envelope = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/">
       <soapenv:Header/>
       <soapenv:Body>
          <tem:EnquiryByRef>
             {inner_payload}
          </tem:EnquiryByRef>
       </soapenv:Body>
    </soapenv:Envelope>"""

        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': 'http://tempuri.org/IEcrComInterface/EnquiryByRef'
        }
        try:
            response = requests.post(service_url, data=envelope, headers=headers, timeout=45, verify=True)
            return self._process_response(response, 'EnquiryResult')
        except Exception as e:
            return {"Status": "Error", "Message": f"Network Error: {e}"}

    def send_apex_cancellation(self):
        """
        Sends a request to cancel the CURRENT IN-PROGRESS operation on the terminal.
        This is NOT for voiding a completed transaction. It is used to interrupt
        an operation like a 'Sale' that is waiting for a card. The result of the
        cancellation will appear in the response of the original, interrupted request.
        """
        service_url = self.service_url
        secure_key = self.secure_key
        tid = self.tid
        mid = self.mid
        ns_data = "http://schemas.datacontract.org/2004/07/"

        # The payload for cancellation only requires the config to identify the terminal.
        inner_payload = f"""
          <tem:webReq xmlns:a="{ns_data}">
            <a:Config>
                <a:EcrCurrencyCode>512</a:EcrCurrencyCode>
                <a:EcrTillerFullName>Python</a:EcrTillerFullName>
                <a:EcrTillerUserName>flan</a:EcrTillerUserName>
                <a:MerchantSecureKey>{secure_key}</a:MerchantSecureKey>
                <a:Mid>{mid}</a:Mid>
                <a:Tid>{tid}</a:Tid>
            </a:Config>
          </tem:webReq>
        """

        envelope = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/">
       <soapenv:Header/>
       <soapenv:Body>
          <tem:RequestCancellation>
             {inner_payload}
          </tem:RequestCancellation>
       </soapenv:Body>
    </soapenv:Envelope>"""

        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': 'http://tempuri.org/IEcrComInterface/RequestCancellation'
        }
        try:
            response = requests.post(service_url, data=envelope, headers=headers, timeout=45, verify=True)
            return self._process_response(response, 'RequestCancellationResult')
        except Exception as e:
            return {"Status": "Error", "Message": f"Network Error: {e}"}