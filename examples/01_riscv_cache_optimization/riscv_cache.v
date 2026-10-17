// Direct-mapped L1 Instruction/Data Cache Module (Verilog-2001)
// Baseline contains a critical hazard detection bug and slow unpipelined hit logic
module riscv_cache #(
    parameter ADDR_WIDTH = 32,
    parameter DATA_WIDTH = 32,
    parameter LINE_SIZE  = 64, // 64 bits = 2 words
    parameter NUM_LINES  = 16
)(
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  req_val,
    output wire                  req_rdy,
    input  wire [ADDR_WIDTH-1:0] req_addr,
    input  wire [DATA_WIDTH-1:0] req_wdata,
    input  wire                  req_wen,
    output reg                   resp_val,
    output reg  [DATA_WIDTH-1:0] resp_rdata,
    output reg                   resp_hit
);

    localparam OFFSET_WIDTH = 3; // 8 bytes / 2 words
    localparam INDEX_WIDTH  = 4; // 16 lines
    localparam TAG_WIDTH    = ADDR_WIDTH - INDEX_WIDTH - OFFSET_WIDTH; // 25 bits

    // Suppress unused lower address bits (byte offset in 32-bit word)
    /* verilator lint_off UNUSEDSIGNAL */
    wire [1:0] unused_byte_offset = req_addr[1:0];
    /* verilator lint_on UNUSEDSIGNAL */

    // Storage arrays
    reg [TAG_WIDTH-1:0]  tag_array  [0:NUM_LINES-1];
    reg [LINE_SIZE-1:0]  data_array [0:NUM_LINES-1];
    reg                  valid_array[0:NUM_LINES-1];

    wire [INDEX_WIDTH-1:0]  req_index  = req_addr[INDEX_WIDTH+OFFSET_WIDTH-1 : OFFSET_WIDTH];
    wire [TAG_WIDTH-1:0]    req_tag    = req_addr[ADDR_WIDTH-1 : INDEX_WIDTH+OFFSET_WIDTH];
    wire                    req_offset = req_addr[2]; // word select

    assign req_rdy = 1'b1;

    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            resp_val   <= 1'b0;
            resp_rdata <= {DATA_WIDTH{1'b0}};
            resp_hit   <= 1'b0;
            for (i = 0; i < NUM_LINES; i = i + 1) begin
                valid_array[i] <= 1'b0;
                tag_array[i]   <= {TAG_WIDTH{1'b0}};
                data_array[i]  <= {LINE_SIZE{1'b0}};
            end
        end else if (req_val) begin
            // Check hit condition
            if (valid_array[req_index] && (tag_array[req_index] == req_tag)) begin
                resp_hit <= 1'b1;
                resp_val <= 1'b1;
                if (req_offset)
                    resp_rdata <= data_array[req_index][63:32];
                else
                    resp_rdata <= data_array[req_index][31:0];

                if (req_wen) begin
                    if (req_offset)
                        data_array[req_index][63:32] <= req_wdata;
                    else
                        data_array[req_index][31:0]  <= req_wdata;
                end
            end else begin
                // Cache Miss: Line refill simulation
                resp_hit <= 1'b0;
                resp_val <= 1'b1;
                valid_array[req_index] <= 1'b1;
                tag_array[req_index]   <= req_tag;
                if (req_wen) begin
                    if (req_offset)
                        data_array[req_index] <= {req_wdata, 32'hDEADBEEF};
                    else
                        data_array[req_index] <= {32'hDEADBEEF, req_wdata};
                    resp_rdata <= req_wdata;
                end else begin
                    data_array[req_index] <= {32'hBEEFCAFE, 32'hCAFEBABE};
                    resp_rdata <= req_offset ? 32'hBEEFCAFE : 32'hCAFEBABE;
                end
            end
        end else begin
            resp_val <= 1'b0;
        end
    end

endmodule
