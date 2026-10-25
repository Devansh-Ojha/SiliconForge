default:
	@echo "Targets: verilate, build, run, clean"

verilate:
	verilator -Wall -Wno-UNUSEDSIGNAL --cc cdc_fifo.v --exe sim_main.cpp

build: verilate
	$(MAKE) -C obj_dir -f Vcdc_fifo.mk Vcdc_fifo

run: build
	./obj_dir/Vcdc_fifo

clean:
	rm -rf obj_dir
