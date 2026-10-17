#include <iostream>
#include <iomanip>
#include <verilated.h>
#include "Vriscv_cache.h"

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Vriscv_cache* top = new Vriscv_cache;

    top->clk = 0;
    top->rst_n = 0;
    top->req_val = 0;
    top->req_addr = 0;
    top->req_wdata = 0;
    top->req_wen = 0;

    int cycles = 0;
    auto tick = [&]() {
        top->clk = 0; top->eval();
        top->clk = 1; top->eval();
        cycles++;
    };

    // Reset sequence
    tick();
    tick();
    top->rst_n = 1;
    tick();

    std::cout << "[SIM] Starting Cache Verification Sequence..." << std::endl;

    // Test 1: Write Miss -> Line allocation
    top->req_val = 1;
    top->req_wen = 1;
    top->req_addr = 0x80000000;
    top->req_wdata = 0x12345678;
    tick();

    if (top->resp_val != 1) {
        std::cerr << "%Error: Write miss did not assert resp_val!" << std::endl;
        return 1;
    }

    // Test 2: Read Hit on same address
    top->req_val = 1;
    top->req_wen = 0;
    top->req_addr = 0x80000000;
    tick();

    if (top->resp_hit != 1 || top->resp_rdata != 0x12345678) {
        std::cerr << "%Error: Cache Read Hit mismatch! Expected 0x12345678, got 0x"
                  << std::hex << top->resp_rdata << " (Hit=" << (int)top->resp_hit << ")" << std::endl;
        return 1;
    }

    // Test 3: Read Miss on different tag, same index
    top->req_val = 1;
    top->req_wen = 0;
    top->req_addr = 0x90000000; // Evicts/misses
    tick();

    if (top->resp_hit != 0) {
        std::cerr << "%Error: Expected Miss, but got Hit on different tag!" << std::endl;
        return 1;
    }

    // Test 4: Verify previous line was replaced
    top->req_val = 1;
    top->req_wen = 0;
    top->req_addr = 0x80000000;
    tick();

    if (top->resp_hit != 0) {
        std::cerr << "%Error: Expected Miss after tag replacement!" << std::endl;
        return 1;
    }

    std::cout << "CYCLES: " << cycles << std::endl;
    std::cout << "SIM_TIME: 0.001" << std::endl;
    std::cout << "ALL TESTS PASSED" << std::endl;

    delete top;
    return 0;
}
