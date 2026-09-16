import os
from datetime import datetime, timedelta
import xarray as xr

import copernicusmarine
import hydra
from omegaconf import DictConfig


def get_cmems_credentials() -> tuple[str, str]:
    username = os.getenv("CMEMS_USERNAME")
    password = os.getenv("CMEMS_PASSWORD")

    if not username or not password:
        raise EnvironmentError(
            "Missing CMEMS credentials. " \
            "Set CMEMS_USERNAME and CMEMS_PASSWORD, " \
            "or place them in ~/.cylc-seacofs.env."
        )

    return username.strip(), password.strip()


@hydra.main(config_path=".", config_name="download_ocean_cmems-mercator_eac", version_base=None)
def run(cfg: DictConfig):
    cycle = cfg.schedule.cycle

    if cycle is None:
        raise ValueError("'schedule.cycle' must be provided (e.g., schedule.cycle=20260101T0000Z)")

    cycle = datetime.strptime(cycle, '%Y%m%dT%H%MZ')

    username, password = get_cmems_credentials()

    for var, kwargs in cfg.task.items():

        ## deflate
        dataset_id = kwargs.dataset_id
        outfile = kwargs.outfile
        fc_horizon = kwargs.fc_horizon
        minimum_longitude = kwargs.minimum_longitude
        maximum_longitude = kwargs.maximum_longitude
        minimum_latitude = kwargs.minimum_latitude
        maximum_latitude = kwargs.maximum_latitude
        pad = kwargs.pad

        ## format the outfile string with the cycle
        outfile = cycle.strftime(kwargs.outfile)

        ## ensure output directory exists
        outdir = os.path.dirname(outfile)
        if not os.path.exists(outdir):
            os.makedirs(outdir, exist_ok=True)

        ## define start and end datetime
        start_datetime = cycle.strftime('%Y-%m-%dT%H:%M:%S')
        end_datetime = (cycle + timedelta(days=int(fc_horizon.rstrip('D')))).strftime('%Y-%m-%dT%H:%M:%S')

        ds = copernicusmarine.open_dataset(
            dataset_id=dataset_id,
            username=username,
            password=password,
            minimum_longitude=minimum_longitude-pad,
            maximum_longitude=maximum_longitude+pad,
            minimum_latitude=minimum_latitude-pad,
            maximum_latitude=maximum_latitude+pad,
            start_datetime= start_datetime,
            end_datetime= end_datetime,
        )

        ds = ds.convert_calendar('proleptic_gregorian')
        ds.to_netcdf(outfile) 

        ## check if the file was downloaded successfully
        if not os.path.isfile(outfile):
            raise FileNotFoundError(f"Failed to download '{var}' data for cycle {cycle}. Expected file not found at {outfile}.")

    return 0


if __name__ == "__main__":
    status = run()

