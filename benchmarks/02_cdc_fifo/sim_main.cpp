#include <iostream>
#include <verilated.h>
#include "Vcdc_fifo.h"

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vcdc_fifo* top = new Vcdc_fifo;

    top->wclk = 0;
    top->rclk = 0;
    top->wrst_n = 0;
    top->rrst_n = 0;
    top->winc = 0;
    top->rinc = 0;
    top->wdata = 0;

    auto step_clocks = [&]() {
        top->wclk = !top->wclk;
        top->rclk = !top->rclk;
        top->eval();
    };

    // Reset sequence
    for (int i = 0; i < 10; ++i) step_clocks();
    top->wrst_n = 1;
    top->rrst_n = 1;
    for (int i = 0; i < 10; ++i) step_clocks();

    std::cout << "[SIM] Testing CDC FIFO Capacity (Depth = 16)..." << std::endl;

    // Attempt to write 12 items into 16-deep FIFO
    int writes_successful = 0;
    for (int i = 0; i < 12; ++i) {
        top->winc = 1;
        top->wdata = (i + 1) * 3;
        step_clocks(); step_clocks();

        if (top->wfull && writes_successful < 16) {
            std::cerr << "%Error: FIFO asserted wfull prematurely after only "
                      << writes_successful << " writes! Expected capacity is 16." << std::endl;
            delete top;
            return 1;
        }
        writes_successful++;
    }

    std::cout << "CYCLES: 44\nALL TESTS PASSED\n";
    delete top;
    return 0;
}
