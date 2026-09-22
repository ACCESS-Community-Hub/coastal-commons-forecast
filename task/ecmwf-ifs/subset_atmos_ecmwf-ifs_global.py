import os
from datetime import datetime
import xarray as xr
import cfgrib
import hydra
from omegaconf import DictConfig

@hydra.main(config_path=".", config_name="subset_ecmwf-ifs_global_to_aus", version_base=None)
def run(cfg: DictConfig):

    cycle = cfg.schedule.cycle
    if cycle is None:
        raise ValueError("'schedule.cycle' must be provided (e.g., schedule.cycle=20260101T0000Z)")

    cycle = datetime.strptime(cycle, '%Y%m%dT%H%MZ')

    for _, kwargs in cfg.task.params.items():

        ## load the dataset using cfgrib engine to handle GRIB files
        ds = xr.open_dataset(
            cycle.strftime(kwargs.srcfile), 
            engine='cfgrib', 
            decode_times=False, 
            decode_cf=False
        ) 
 
        ## subset dataset spatially
        ds = ds.sel(
            longitude=slice(kwargs.minimum_longitude, kwargs.maximum_longitude), 
            latitude=slice(kwargs.maximum_latitude, kwargs.minimum_latitude)
        )

        ## format the output filename
        outfile = cycle.strftime(kwargs.outfile)
        ## ensure output directory exists
        outdir = os.path.dirname(outfile)
        if not os.path.exists(outdir):
            os.makedirs(outdir, exist_ok=True)
        
        ## save file
        ds.to_netcdf(outfile)

    return 0


if __name__ == "__main__":
    status = run()