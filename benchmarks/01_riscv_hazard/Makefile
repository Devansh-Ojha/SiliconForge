default:
	@echo "Targets: verilate, build, run, clean"

verilate:
	verilator -Wall --cc hazard_unit.v --exe sim_main.cpp

build: verilate
	$(MAKE) -C obj_dir -f Vhazard_unit.mk Vhazard_unit

run: build
	./obj_dir/Vhazard_unit

clean:
	rm -rf obj_dir
