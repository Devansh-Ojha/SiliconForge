// Benchmark 01: RISC-V Hazard Detection & Forwarding Unit
// Contains a planted bug where EX/MEM hazard priority fails to override ID/EX hazard
module riscv_hazard_unit (
    input  wire [4:0] id_rs1,
    input  wire [4:0] id_rs2,
    input  wire [4:0] ex_rd,
    input  wire       ex_regwrite,
    input  wire [4:0] mem_rd,
    input  wire       mem_regwrite,
    output reg  [1:0] forward_a, // 00: None, 01: From MEM, 10: From EX
    output reg  [1:0] forward_b
);

    always @(*) begin
        // Forward A default
        forward_a = 2'b00;
        forward_b = 2'b00;

        // Forward A Logic
        // BUG: Inverted priority! If both EX and MEM write to rs1, MEM erroneously wins
        if (mem_regwrite && (mem_rd != 5'd0) && (mem_rd == id_rs1)) begin
            forward_a = 2'b01;
        end else if (ex_regwrite && (ex_rd != 5'd0) && (ex_rd == id_rs1)) begin
            forward_a = 2'b10;
        end

        // Forward B Logic
        if (mem_regwrite && (mem_rd != 5'd0) && (mem_rd == id_rs2)) begin
            forward_b = 2'b01;
        end else if (ex_regwrite && (ex_rd != 5'd0) && (ex_rd == id_rs2)) begin
            forward_b = 2'b10;
        end
    end

endmodule
