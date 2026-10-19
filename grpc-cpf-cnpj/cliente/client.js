const grpc = require("@grpc/grpc-js");
const protoLoader = require("@grpc/proto-loader");

const PROTO_PATH = __dirname + "/validador.proto";

const packageDefinition = protoLoader.loadSync(PROTO_PATH, {
  keepCase: true,
  longs: String,
  enums: String,
  defaults: true,
  oneofs: true,
});

const validadorProto = grpc.loadPackageDefinition(packageDefinition).validador;

function main() {
  const documentType = process.argv[2];
  const value = process.argv[3];

  if (!documentType || !value) {
    console.log("Uso: node client.js <CPF|CNPJ> <valor>");
    return;
  }

  const client = new validadorProto.Validador(
    "localhost:50051",
    grpc.credentials.createInsecure()
  );

  client.ValidarDocumento(
    { document_type: documentType, value: value },
    function (err, response) {
      if (err) {
        console.error("Erro:", err.message);
        return;
      }
      console.log(response.message + ": " + response.cpf_cnpj);
    }
  );
}

main();
