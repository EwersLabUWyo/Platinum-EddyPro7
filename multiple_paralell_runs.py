## python script to create multiple separate eddypro configurations using different settings, and to then run all of those in parallel
import sys
from pathlib import Path
import itertools
import multiprocessing

from tqdm import tqdm

sys.path.append('/Users/alex/Documents/Work/UWyo/Research/Flux Pipeline Project/Eddypro-ec-testing/src/python')
from python.eddyproconfigeditor import EddyproConfigEditor
from run_eddypro_parallel import call, make_eddypro_calls

if __name__ == '__main__':
    
    # setup parent directory
    wd = Path('/Users/alex/Documents/Work/UWyo/Research/Flux Pipeline Project/Eddypro-ec-testing/eddypro_compare_parallel')

    # configure base file
    base_env = wd / 'base'
    base = EddyproConfigEditor(reference_ini=base_env / 'ini/base.eddypro')
    # save a reference file as a copy of base
    reference_ini = wd / 'reference.eddypro'
    base.to_eddypro(reference_ini, out_path=base_env / 'output')
    # save base parallel files to their own directories
    base.to_eddypro_parallel(base_env / 'ini', file_duration=30, out_path=base_env / 'output')

    # methods: rotations (none, dr, tr), timelags (none, covmaxdef, covmax), turbfluct (block, dt, rm, erm)
    # naming convention: tiltcorr#-timelag#-turbfluct#
    pbar = tqdm(
        itertools.product(
            [0, 1, 2],
            [0, 2, 3],
            [0, 1, 2, 3]
        ),
        total=3*3*4
    )
    for tiltcorr, timelag, turbfluct in pbar:
        if tiltcorr*100 + timelag*10 + turbfluct < 101:
            pass
        else:
            pbar.set_postfix(dict(method=f'{tiltcorr}-{timelag}-{turbfluct}'))

            # set up directory structure
            environment = wd / f'tiltcorr{tiltcorr}-timelag{timelag}-turbfluct{turbfluct}'
            ini_dir = environment / 'ini'
            stdout_dir = environment / 'stdout'
            tmp_dir = environment / 'tmp'
            bin_dir = environment / 'bin'
            Path.mkdir(environment, exist_ok=True)
            Path.mkdir(ini_dir, exist_ok=True)
            Path.mkdir(stdout_dir, exist_ok=True)
            Path.mkdir(tmp_dir, exist_ok=True)
            master_fn = ini_dir / 'master.eddypro'

            # modify ini files
            ini = EddyproConfigEditor(reference_ini=reference_ini)
            ini.Adv.Proc.set_axis_rotations_for_tilt_correction
            ini.Adv.Proc.set_axis_rotations_for_tilt_correction(method=tiltcorr)
            ini.Adv.Proc.set_timelag_compensations(method=timelag)
            ini.Adv.Proc.set_turbulent_fluctuations(detrend_method=turbfluct)
            ini.to_eddypro(master_fn, out_path=environment / 'output')
            ini.to_eddypro_parallel(ini_dir, file_duration=30, out_path=environment / 'output')

            # run in parallel
            PROJ_FILES = ini_dir.glob('worker*.eddypro')
            eddypro_rp = Path('/Users/alex/Documents/Work/UWyo/Research/Flux Pipeline Project/Eddypro-ec-testing/eddypro_compare_parallel/base/bin/eddypro_rp')
            eddypro_fcc = Path('/Users/alex/Documents/Work/UWyo/Research/Flux Pipeline Project/Eddypro-ec-testing/eddypro_compare_parallel/base/bin/eddypro_fcc')

            eddypro_rp_calls, eddypro_fcc_calls, stdout_files = make_eddypro_calls(
                environment=environment,
                clean_children=True,
                PROJ_FILES=PROJ_FILES,
                eddypro_rp=eddypro_rp,
                eddypro_fcc=eddypro_fcc,
            )
            
            args = [(rp_call, fcc_call, f) for rp_call, fcc_call, f in zip(eddypro_rp_calls, eddypro_fcc_calls, stdout_files)]

            # multiprocessing
            processes = max(multiprocessing.cpu_count() - 1, 1)
            # print(f'\nBeginning EddyPro Runs: {len(args)} runs on {processes} cores\n')
            with multiprocessing.Pool(processes) as p:
                p.map(call, args)