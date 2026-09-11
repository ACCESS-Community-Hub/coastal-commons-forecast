import os
from datetime import datetime, timedelta

import cfgrib
import hydra
from omegaconf import DictConfig
from ecmwf.opendata import Client


def set_product_time_steps(start_datetime: str, end_datetime: str) -> list:
    ## NOTE: MODEL TEMPORAL RESOLUTION
    ##   - Cycles 00z & 12z: 0 to 144 by 3, 150 to 360 by 6.
    ##   - Cycles 06z & 18z: 0 to 144 by 3.

    def generate_time_steps(start: int, end: int, step: int) -> list:
        return [int(f"{hour:02d}") for hour in range(start, end + 1, step)]

    ## determine time steps
    start_date = datetime.strptime(start_datetime, '%Y-%m-%dT%H:%M:%S')
    end_date = datetime.strptime(end_datetime, '%Y-%m-%dT%H:%M:%S')
    delta = int((end_date - start_date).total_seconds() / 3600)  # Convert to hours
    ## 3-hourly steps up to 144 hours
    time_steps = generate_time_steps(0, 144, 3)
    ## 6-hourly steps beyond 144 hours, if applicable
    if delta > 144:
        time_steps += generate_time_steps(150, delta, 6)
    
    return time_steps


@hydra.main(config_path=".", config_name="download_atmos_ecmwf-ifs_global", version_base=None)
def run(cfg: DictConfig):

    cycle = cfg.schedule.cycle
    if cycle is None:
        raise ValueError("'schedule.cycle' must be provided (e.g., schedule.cycle=20260101T0000Z)")

    cycle = datetime.strptime(cycle, '%Y%m%dT%H%MZ')

    ## initialize ECMWF Opendata client
    client = Client(
        source=cfg.task.source,
        model=cfg.task.model,
        resol=cfg.task.resol,
        preserve_request_order=False,
        infer_stream_keyword=True,
    )

    ## loop over each variable block in the config
    for param, kwargs in cfg.task.params.items():

        ## unpack kwargs
        dtype = kwargs.type
        levtype = kwargs.levtype
        fc_horizon = kwargs.fc_horizon
        outfile = cycle.strftime(kwargs.outfile)

        ## ensure output directory exists
        outdir = os.path.dirname(outfile)
        if not os.path.exists(outdir):
            os.makedirs(outdir, exist_ok=True)

        ## determine time steps
        start_datetime = cycle.strftime('%Y-%m-%dT%H:%M:%S')
        end_datetime = (cycle + timedelta(days=int(fc_horizon.rstrip('D')))).strftime('%Y-%m-%dT%H:%M:%S')
        time_steps = set_product_time_steps(start_datetime, end_datetime)

        ## execute the download task
        result = client.retrieve(
            type=dtype,
            levtype=levtype,
            param=param,
            date=cycle.strftime('%Y-%m-%d'),
            time=cycle.strftime('%H'),
            step=time_steps,
            target=outfile
        )

        ## check if the file was downloaded successfully
        if not os.path.isfile(outfile):
            raise FileNotFoundError(f"Failed to download '{param}' data for cycle {cycle}. Expected file not found at {outfile}.")

    return 0


if __name__ == "__main__":
    status = run()
