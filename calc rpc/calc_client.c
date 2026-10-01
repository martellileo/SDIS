#include <stdio.h>
#include <stdlib.h>
#include "calc.h"

void calculadora_prog(char *host, double a, char op, double b) {
    CLIENT *clnt;
    double *result;
    operandos args;

    clnt = clnt_create(host, CALC_PROG, CALC_VERS, "udp");
    if (clnt == NULL) {
        clnt_pcreateerror(host);
        exit(1);
    }

    args.a = a;
    args.op = op;
    args.b = b;

    result = calcular_1(&args, clnt);
    if (result == (double *) NULL) {
        clnt_perror(clnt, "Falha na chamada RPC");
    } else {
        printf("Resultado: %.2f %c %.2f = %.2f\n", args.a, args.op, args.b, *result);
    }

    clnt_destroy(clnt);
}

int main(int argc, char *argv[]) {
    char *host;
    double a, b;
    char op;

    // if (argc != 5) {
    //     printf("Uso correto: %s <servidor_host> <num1> <operador> <num2>\n", argv[0]);
    //     printf("Exemplos:\n");
    //     printf("  %s localhost 10 + 30\n", argv[0]);
    //     printf("  %s localhost 10 \"*\" 30\n", argv[0]);
    //     printf("  %s localhost 100 / 4\n", argv[0]);
    //     exit(1);
    // }

    host = argv[1];
    a = atof(argv[2]);
    op = argv[3][0];
    b = atof(argv[4]);

    calculadora_prog(host, a, op, b);
    
    exit(0);
}