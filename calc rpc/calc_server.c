#include <stdio.h>
#include "calc.h"

double * calcular_1_svc(operandos *argp, struct svc_req *rqstp) {
    static double resultado;
    
    printf("Recebido: %.2f %c %.2f\n", argp->a, argp->op, argp->b);
    
    switch(argp->op) {
        case '+':
            resultado = argp->a + argp->b;
            break;
        case '-':
            resultado = argp->a - argp->b;
            break;
        case '*':
            resultado = argp->a * argp->b;
            break;
        case '/':
            if (argp->b != 0) {
                resultado = argp->a / argp->b;
            } else {
                printf("Erro: Divisao por zero!\n");
                resultado = 0;
            }
            break;
        default:
            printf("Operacao invalida: %c\n", argp->op);
            resultado = 0;
    }
    
    return &resultado;
}