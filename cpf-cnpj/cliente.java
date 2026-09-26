import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.UUID;

public final class cliente {
    private static final int PROTOCOL_VERSION = 1;

    private cliente() {}

    public static void main(String[] args) throws IOException {
        if (args.length < 4) {
            System.err.println("Use: java cliente <server> <port> <CPF|CNPJ> <value>");
            return;
        }

        String host = args[0];
        int port = Integer.parseInt(args[1]);
        String documentType = args[2].toUpperCase();
        String documentValue = args[3];

        if (!documentType.equals("CPF") && !documentType.equals("CNPJ")) {
            System.err.println("Tipo de documento inválido. Use CPF ou CNPJ.");
            return;
        }

        try (Socket socket = new Socket(host, port);
             BufferedReader reader = new BufferedReader(
                     new InputStreamReader(socket.getInputStream(), StandardCharsets.UTF_8));
             BufferedWriter writer = new BufferedWriter(
                     new OutputStreamWriter(socket.getOutputStream(), StandardCharsets.UTF_8))) {
            sendAndPrintResponse(writer, reader, createHelloMessage());

            sendAndPrintResponse(
                    writer,
                    reader,
                    createValidationMessage(documentType, documentValue)
            );

            sendAndPrintResponse(writer, reader, createQuitMessage());
        }
    }

    private static String createHelloMessage() {
        return "{\"type\":\"hello\",\"version\":" + PROTOCOL_VERSION
                + ",\"request_id\":\"" + newRequestId() + "\"}";
    }

    private static String createValidationMessage(String documentType, String value) {
        return "{\"type\":\"validate\",\"version\":" + PROTOCOL_VERSION
                + ",\"request_id\":\"" + newRequestId()
                + "\",\"document_type\":\"" + documentType
                + "\",\"value\":\"" + escapeJson(value) + "\"}";
    }

    private static String createQuitMessage() {
        return "{\"type\":\"quit\",\"version\":" + PROTOCOL_VERSION
                + ",\"request_id\":\"" + newRequestId() + "\"}";
    }

    private static String newRequestId() {
        return UUID.randomUUID().toString();
    }

    private static String escapeJson(String value) {
        return value.replace("\\", "\\\\").replace("\"", "\\\"");
    }

    private static void sendAndPrintResponse(
            BufferedWriter writer, BufferedReader reader, String message
    ) throws IOException {
        writer.write(message);
        writer.newLine();
        writer.flush();
        System.out.println("Client -> " + message);
        System.out.println("Server <- " + reader.readLine());
    }
}
