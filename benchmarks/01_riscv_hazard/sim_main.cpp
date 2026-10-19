#include <iostream>
#include <verilated.h>
#include "Vhazard_unit.h"

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vhazard_unit* top = new Vhazard_unit;

    // Test Case: RAW Hazard Conflict (Both EX and MEM write to same reg x1)
    // EX is younger/closer and MUST take precedence over MEM!
    top->id_rs1 = 1;
    top->id_rs2 = 0;
    top->ex_rd = 1;
    top->ex_regwrite = 1;
    top->mem_rd = 1;
    top->mem_regwrite = 1;

    top->eval();

    if (top->forward_a != 0b10) {
        std::cerr << "%Error: Forward A priority failed! Expected 0b10 (EX stage), got 0b"
                  << (int)top->forward_a << std::endl;
        delete top;
        return 1;
    }

    std::cout << "CYCLES: 1\nALL TESTS PASSED\n";
    delete top;
    return 0;
}
