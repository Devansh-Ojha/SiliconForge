default:
	@echo "Targets: verilate, build, run, clean"

verilate:
	verilator -Wall --cc riscv_cache.v --exe sim_main.cpp

build: verilate
	$(MAKE) -C obj_dir -f Vriscv_cache.mk Vriscv_cache

run: build
	./obj_dir/Vriscv_cache

clean:
	rm -rf obj_dir
