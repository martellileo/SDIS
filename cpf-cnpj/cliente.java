import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.net.Socket;
import java.nio.charset.StandardCharsets;

public final class cliente {
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
            String response = sendAndReadResponse(
                    writer,
                    reader,
                    createValidationMessage(documentType, documentValue)
            );
            System.out.println(response);
        }
    }

    private static String createValidationMessage(String documentType, String value) {
        return "{\"type\":\"validate\",\"document_type\":\"" + documentType
                + "\",\"value\":\"" + escapeJson(value) + "\"}";
    }

    private static String escapeJson(String value) {
        return value.replace("\\", "\\\\").replace("\"", "\\\"");
    }

    private static String sendAndReadResponse(
            BufferedWriter writer, BufferedReader reader, String message
    ) throws IOException {
        writer.write(message);
        writer.newLine();
        writer.flush();
        return reader.readLine();
    }
}
