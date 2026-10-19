struct operandos {
    char op;
    double a;
    double b;
};

program CALC_PROG {
    version CALC_VERS {
        double CALCULAR(operandos) = 1;
    } = 1;
} = 0x23456789;