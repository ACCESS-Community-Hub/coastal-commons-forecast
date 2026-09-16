import os
from os.path import join, basename
from datetime import datetime
import pandas as pd
from urllib.request import urlretrieve

import hydra
from omegaconf import DictConfig

from argopy import ArgoIndex


## NOTE:
## Host options for ArgoIndex:
##
## Full host	                            Shortcut
## -------------------------------------    -------------------
## https://data-argo.ifremer.fr	            http or https
## https://usgodae.org/pub/outgoing/argo	us-http or us-https
## ftp://ftp.ifremer.fr/ifremer/argo	    ftp
## s3://argo-gdac-sandbox/pub/idx	        s3 or aws
##
## https://github.com/euroargodev/argopy/blob/802ef617e9a33a53c15b68d0876691a25d8b8c83/docs/advanced-tools/stores/argoindex.rst#L69

## NOTE:
## argopy Cheatsheet:
##    - https://argopy.readthedocs.io/en/latest/_downloads/01518516cd638e9c2347623d268c585e/argopy-cheatsheet.pdf

## TODO:
## - Implement error handling for "ftplib.error_temp: 421 There are too many connected users, please try later."
## - Implement error handling for failed downloads.
## - Implement 'hosts' fallback in order until profiles are found

@hydra.main(config_path=".", config_name="download_ocean_gdac-argo_eac", version_base=None)
def run(cfg: DictConfig):


    ## unpack config inputs
    cycle = cfg.schedule.cycle
    kwargs = cfg.task.profile

    if cycle is None:
        raise ValueError("'schedule.cycle' must be provided (e.g., schedule.cycle=20260101T0000Z)")

    ## format the cycle string into datetime object
    cycle = datetime.strptime(cycle, '%Y%m%dT%H%MZ')

    ## define end date
    end_date = cycle.strftime('%Y-%m-%d')

    ## deflate the kwargs
    outdir = kwargs.outdir
    longitude_min = kwargs.longitude_min
    longitude_max = kwargs.longitude_max
    latitude_min = kwargs.latitude_min
    latitude_max = kwargs.latitude_max
    lookback_period = kwargs.lookback_period
    hosts = kwargs.hosts

    ## define start date based on 'lookback_period'
    tdelta = pd.to_timedelta(lookback_period)
    start_date_dt = datetime.strptime(end_date, '%Y-%m-%d') - tdelta
    start_date = start_date_dt.strftime('%Y-%m-%d')

    ## ensure output directory exists
    outdir = start_date_dt.strftime(outdir)
    if not os.path.exists(outdir):
        os.makedirs(outdir, exist_ok=True)

    for host in hosts:
        ## load server index for given host
        index = ArgoIndex(host=host)
        ## query index for profiles within the specified region and time period
        index_subset = index.query.box([
            longitude_min,
            longitude_max,
            latitude_min,
            latitude_max,
            start_date,
            end_date
        ])

        ## get number of files found
        n_files = index_subset.N_FILES

        ## check if any profiles were found in given host, if not, try next host (if any)
        print(f"Fetching '{index.host}'")
        if n_files == 0:
            print("No Argo profiles found for the specified region and time period.")
            if host == hosts[-1]:
                raise SystemExit
            else:
                print("Trying next host...")
                continue
        else:
            print(f"Number of profiles to download: {n_files}")

        ## perform downloads
        for uri in index_subset.uri:
            ## define output file path
            outfile = os.path.join(outdir, basename(uri))
            ## download
            if not os.path.exists(outfile):
                print(f"Downloading from GDAC: {uri} to {outfile}")
                _ = urlretrieve(uri, outfile)
                ## TODO: implement error handling
            else:
                print(f"File already exists: {outfile}, skipping download.")

        ## dump info_dict to json file
        index_file = join(outdir, f"index_argo_{start_date_dt.strftime('%Y%m%d')}.txt")
        _ = index_subset.to_indexfile(index_file)
        print(f"Index file saved to: {index_file}")

    return 0


if __name__ == "__main__":
    status = run()
