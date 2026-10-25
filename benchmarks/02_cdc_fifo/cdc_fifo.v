// Benchmark 02: Asynchronous Clock Domain Crossing (CDC) FIFO (Dual-Clock Gray Code)
module cdc_fifo #(
    parameter DATA_WIDTH = 8,
    parameter ADDR_DEPTH = 4  // 16-entry FIFO
)(
    // Write Clock Domain
    input  wire                  wclk,
    input  wire                  wrst_n,
    input  wire                  winc,
    input  wire [DATA_WIDTH-1:0] wdata,
    output reg                   wfull,

    // Read Clock Domain
    input  wire                  rclk,
    input  wire                  rrst_n,
    input  wire                  rinc,
    output wire [DATA_WIDTH-1:0] rdata,
    output reg                   rempty
);

    localparam FIFO_SIZE = 1 << ADDR_DEPTH;

    reg [DATA_WIDTH-1:0] mem [0:FIFO_SIZE-1];

    reg [ADDR_DEPTH:0] wptr_bin, wptr_gray;
    reg [ADDR_DEPTH:0] rptr_bin, rptr_gray;

    // Multi-flop synchronizers
    reg [ADDR_DEPTH:0] wptr_gray_sync1, wptr_gray_sync2;
    reg [ADDR_DEPTH:0] rptr_gray_sync1, rptr_gray_sync2;

    // Memory write
    always @(posedge wclk) begin
        if (winc && !wfull)
            mem[wptr_bin[ADDR_DEPTH-1:0]] <= wdata;
    end

    // Memory read
    assign rdata = mem[rptr_bin[ADDR_DEPTH-1:0]];

    // Synchronize rptr_gray to wclk domain
    always @(posedge wclk or negedge wrst_n) begin
        if (!wrst_n) begin
            rptr_gray_sync1 <= {(ADDR_DEPTH+1){1'b0}};
            rptr_gray_sync2 <= {(ADDR_DEPTH+1){1'b0}};
        end else begin
            rptr_gray_sync1 <= rptr_gray;
            rptr_gray_sync2 <= rptr_gray_sync1;
        end
    end

    // Synchronize wptr_gray to rclk domain
    always @(posedge rclk or negedge rrst_n) begin
        if (!rrst_n) begin
            wptr_gray_sync1 <= {(ADDR_DEPTH+1){1'b0}};
            wptr_gray_sync2 <= {(ADDR_DEPTH+1){1'b0}};
        end else begin
            wptr_gray_sync1 <= wptr_gray;
            wptr_gray_sync2 <= wptr_gray_sync1;
        end
    end

    // Write pointer management
    wire [ADDR_DEPTH:0] wptr_bin_next = wptr_bin + (winc && !wfull ? {{(ADDR_DEPTH){1'b0}}, 1'b1} : {(ADDR_DEPTH+1){1'b0}});
    wire [ADDR_DEPTH:0] wptr_gray_next = (wptr_bin_next >> 1) ^ wptr_bin_next;

    // Full condition generation (in wclk domain)
    // Planted Bug: Incorrect comparison causing premature full assertion
    wire wfull_val = (wptr_gray_next == rptr_gray_sync2);

    always @(posedge wclk or negedge wrst_n) begin
        if (!wrst_n) begin
            wptr_bin  <= {(ADDR_DEPTH+1){1'b0}};
            wptr_gray <= {(ADDR_DEPTH+1){1'b0}};
            wfull     <= 1'b0;
        end else begin
            wptr_bin  <= wptr_bin_next;
            wptr_gray <= wptr_gray_next;
            wfull     <= wfull_val;
        end
    end

    // Read pointer management
    wire [ADDR_DEPTH:0] rptr_bin_next = rptr_bin + (rinc && !rempty ? {{(ADDR_DEPTH){1'b0}}, 1'b1} : {(ADDR_DEPTH+1){1'b0}});
    wire [ADDR_DEPTH:0] rptr_gray_next = (rptr_bin_next >> 1) ^ rptr_bin_next;

    wire rempty_val = (rptr_gray_next == wptr_gray_sync2);

    always @(posedge rclk or negedge rrst_n) begin
        if (!rrst_n) begin
            rptr_bin  <= {(ADDR_DEPTH+1){1'b0}};
            rptr_gray <= {(ADDR_DEPTH+1){1'b0}};
            rempty    <= 1'b1;
        end else begin
            rptr_bin  <= rptr_bin_next;
            rptr_gray <= rptr_gray_next;
            rempty    <= rempty_val;
        end
    end

endmodule
