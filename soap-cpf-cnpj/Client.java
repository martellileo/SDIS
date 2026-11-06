import java.io.File;
import java.io.StringReader;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import javax.xml.XMLConstants;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.transform.dom.DOMSource;
import javax.xml.validation.Schema;
import javax.xml.validation.SchemaFactory;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;
import org.xml.sax.InputSource;

public class Client {
    private static final String SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/";
    private static final String TNS = "http://sdis.ifsp.edu.br/validador";

    public static void main(String[] args) throws Exception {
        if (args.length < 2) {
            System.out.println("Uso: java Client.java <CPF|CNPJ> <valor> [url]");
            return;
        }
        String docType = args[0];
        String val = args[1];
        String url = args.length > 2 ? args[2] : "http://localhost:8000/soap";

        File xsdFile = new File("validador.xsd");
        if (!xsdFile.exists()) xsdFile = new File("soap-cpf-cnpj/validador.xsd");
        Schema schema = SchemaFactory.newInstance(XMLConstants.W3C_XML_SCHEMA_NS_URI)
                .newSchema(xsdFile);
        DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
        dbf.setNamespaceAware(true);

        String reqPayload = "<tns:ValidarDocumentoRequest xmlns:tns=\"" + TNS + "\">"
                + "<tns:document_type>" + docType + "</tns:document_type>"
                + "<tns:value>" + val + "</tns:value>"
                + "</tns:ValidarDocumentoRequest>";

        // Valida requisição contra o XSD antes de enviar
        Document reqDoc = dbf.newDocumentBuilder().parse(new InputSource(new StringReader(reqPayload)));
        schema.newValidator().validate(new DOMSource(reqDoc));

        String soapEnvelope = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
                + "<soap:Envelope xmlns:soap=\"" + SOAP_NS + "\">"
                + "<soap:Body>" + reqPayload + "</soap:Body>"
                + "</soap:Envelope>";

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("Content-Type", "text/xml; charset=utf-8")
                .header("SOAPAction", "\"" + TNS + "/ValidarDocumento\"")
                .POST(HttpRequest.BodyPublishers.ofString(soapEnvelope))
                .build();

        HttpResponse<String> response = HttpClient.newHttpClient()
                .send(request, HttpResponse.BodyHandlers.ofString());

        Document respDoc = dbf.newDocumentBuilder().parse(new InputSource(new StringReader(response.body())));
        NodeList faults = respDoc.getElementsByTagNameNS(SOAP_NS, "Fault");
        if (faults.getLength() > 0) {
            System.err.println("SOAP Fault: " + faults.item(0).getTextContent());
            return;
        }

        Element respElem = (Element) respDoc.getElementsByTagNameNS(TNS, "ValidarDocumentoResponse").item(0);
        // Valida resposta contra o XSD ao receber
        schema.newValidator().validate(new DOMSource(respElem));

        String msg = respElem.getElementsByTagNameNS(TNS, "message").item(0).getTextContent();
        String norm = respElem.getElementsByTagNameNS(TNS, "cpf_cnpj").item(0).getTextContent();
        System.out.println(msg + ": " + norm);
    }
}
