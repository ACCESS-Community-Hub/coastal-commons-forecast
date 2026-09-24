import os
import re
import numpy as np
from datetime import datetime
import xarray as xr
import hydra
from omegaconf import DictConfig

def _is_latitude_descending(lat: np.ndarray) -> bool:
    """
    Check if the latitude values are in descending order.
    """
    return lat[0] > lat[-1]


def deacumulate_variable(data: np.ndarray, time_steps: np.ndarray) -> np.ndarray:
    """
    Convert accumulated variable (e.g., precipitation, flux) to rate (per second).

    Parameters:
    data (numpy.ndarray): Accumulated variable data
    time_steps (numpy.ndarray): Time steps in seconds between data points.

    Returns:
    numpy.ndarray: Deaccumulated rate data
    """
    accum = data.copy()
    rate = np.zeros_like(data)
    for it in range(data.shape[0]):
        if it == 0:
            ## if first time step equal to zero (due to accumulation from tstep = 0)
            ## set values as rate of change from tstep=0 to tstep=1
            if np.all(accum[it, :, :] == 0):
                rate[it, :, :] = (accum[it + 1, :, :] - accum[it, :, :]) / time_steps[it + 1]
            else:
                rate[it, :, :] = accum[it, :, :] / time_steps[it]
        else:
            rate[it, :, :] = (accum[it, :, :] - accum[it - 1, :, :]) / time_steps[it - 1]
    return rate


def get_time_steps(time: xr.DataArray) -> np.ndarray:
    """
    Get the time step(s) in seconds from an xarray DataArray of time.

    Parameters:
    time (xr.DataArray): Time coordinate from a NetCDF file.

    Returns:
    numpy.ndarray: Array of time steps in seconds.
    """

    return time.diff('time').values.astype('timedelta64[s]').astype(int)


def get_bbox(roms_grid_file: str, pad: float) -> list:
    """
    Determine the bounding box (bbox) based on the ROMS grid extent.

    Parameters:
    roms_grid_file (str): Path to the ROMS grid file.
    pad (float): Padding value to extend the bbox (in degrees).

    Returns:
    list: Bounding box in the format [lon_min, lon_max, lat_min, lat_max].
    """
    grd = xr.open_dataset(roms_grid_file)
    bbox = [
        grd.lon_rho.min().values - pad,
        grd.lon_rho.max().values + pad,
        grd.lat_rho.min().values - pad,
        grd.lat_rho.max().values + pad,
    ]
    return bbox


def compute_relative_humidity(t2d: np.ndarray, t2: np.ndarray) -> np.ndarray:
    """
    Compute relative humidity from 2m dewpoint temp and 2m air temp
    Q = 100 * Es(2d)/Es(2t)  
    with Es(T) = 6.11* 10^(7.5 * T/(237.7 + T))  {T in Celsius}  
    """

    t2d = t2d - 273.15  # in Celsius
    t2 = t2 - 273.15  # in Celsius
    ratio = 7.5 * (t2d/(237.7 + t2d) - t2/(237.7 + t2))
    rh =  100 * (10**ratio)
    rh[rh>100.0] = 100.0
    rh[rh<0.0] = 0.0

    return rh

@hydra.main(config_path=".", config_name="process_atmos_ecmwf-ifs_global_to_roms_eac", version_base=None)
def run(cfg: DictConfig):

    cycle = cfg.schedule.cycle
    if cycle is None:
        raise ValueError("'schedule.cycle' must be provided (e.g., schedule.cycle=20260101T0000Z)")

    cycle = datetime.strptime(cycle, '%Y%m%dT%H%MZ')

    for _, kwargs in cfg.task.params.items():

        derived_variable = kwargs.get('derived_variable', False)

        if derived_variable == False:
            ds = xr.open_dataset(cycle.strftime(kwargs.srcfile), decode_times=False, decode_cf=False) 
        elif derived_variable == True:
            srcfile = [cycle.strftime(value) for _, value in kwargs.srcfile.items()]
            ds = xr.open_mfdataset(srcfile, decode_times=False, decode_cf=False)       

        ## subset dataset spatially
        bbox = get_bbox(kwargs.roms_grid_file, kwargs.pad)
        ds = ds.sel(longitude=slice(bbox[0], bbox[1]), latitude=slice(bbox[3], bbox[2]))

        ## set the new time coordinate
        ds = ds.rename({'time': 'tref'})
        step_attrs = ds['step'].attrs
        times = ds.tref.values + (ds.step.values * 3600)
        ds = ds.rename({'step': 'time'})
        ds = ds.assign_coords(time=times)
        ds['time'].attrs = step_attrs
        ds['time'].attrs['units'] = ds['tref'].attrs['units']

        ## NOTE: ROMS requires latitude to be in ascending order.
        ##    see issue with descending latitudes:
        ##    https://www.myroms.org/forum/viewtopic.php?p=21353&hilit=_frc+large+Min+MAx+values#p21353
        if _is_latitude_descending(ds.latitude.values):
            ds = ds.sortby('latitude', ascending=True)
            ds['latitude'].attrs['stored_direction'] = 'increasing'

        ## convert fluxes units from J m**-2 to W m**-2
        if ('strd' in ds.variables) or ('ssrd' in ds.variables):
            time_steps = get_time_steps(ds['time'])
            for vid in ['strd', 'ssrd']:
                if vid not in ds.variables:
                    continue
                attrs = ds[vid].attrs
                vrate = deacumulate_variable(ds[vid].values, time_steps=time_steps)
                ds[vid] = xr.DataArray(vrate, dims=['time', 'latitude', 'longitude'], coords={'time': ds.time})
                ds[vid].attrs = attrs
                ds[vid].attrs['units'] = 'W m-2'
                ds[vid].attrs['GRIB_stepType'] = 'instant'

        ## process relative humidity
        if derived_variable == False and 'r' in ds.variables:
            ds['r'] = ds['r'].isel(isobaricInhPa=0)  ## select the first isobaric level (i.e. 10 m)
        elif derived_variable == True and 'd2m' in ds.variables and 't2m' in ds.variables:
            ## compute from 2d (dewpoint) and 2t (air temp)
            attrs = ds['d2m'].attrs
            rh = compute_relative_humidity(ds['d2m'].values, ds['t2m'].values)
            ds['r'] = xr.DataArray(rh, dims=['time', 'latitude', 'longitude'], coords={'time': ds.time})
            ds['r'].attrs = attrs
            ds['r'].attrs['GRIB_name'] = ''
            ds['r'].attrs['GRIB_units'] = ''
            ds['r'].attrs['GRIB_paramId'] = ''
            ds['r'].attrs['GRIB_cfVarName'] = ''
            ds['r'].attrs['GRIB_short-name'] = ''
            ds['r'].attrs['long_name'] = 'Relative humidity'
            ds['r'].attrs['units'] = '%'

        ## drop variable 'heightAboveGround' if it exists
        ##  NOTE: see issue with 'cfgrib' 
        ##  https://github.com/ecmwf/cfgrib/issues/263
        if 'heightAboveGround' in ds.variables:
            ds = ds.drop_vars('heightAboveGround')

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
