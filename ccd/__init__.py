from ccd.procedures import determine_fit_procedure as __determine_fit_procedure
import numpy as np
from ccd import app
import importlib
from .version import __version__
from .version import __algorithm__
from .version import __name

logger = app.logging.getLogger(__name)
defaults = app.defaults


def attr_from_str(value):
    """Returns a reference to the full qualified function, attribute or class.

    Args:
        value = Fully qualified path (e.g. 'ccd.models.lasso.fitted_model')

    Returns:
        A reference to the target attribute (e.g. fitted_model)
    """
    module, target = value.rsplit('.', 1)
    try:
        obj = importlib.import_module(module)
        return getattr(obj, target)
    except (ImportError, AttributeError) as e:
        logger.debug(e)
        return None


def __result_to_detection(change_tuple, processing_mask, procedure):
    """Transforms results of change.detect to the detections dict.

    Args:
        change_tuple: A tuple as returned from change.detect
            (start_day, end_day, models, errors, magnitudes_)
        processing_mask: boolean array showing which values were included in the fitting
            of the change models
        procedure: method that was used to generate the change models

    Returns: A dict representing a change detection

        {algorithm: 'pyccd:x.x.x',
         processing_mask: (bool, bool, ...),
         procedure: string,
         change_models: [
             {start_day: int,
              end_day: int,
              break_day: int,
              observation_count: int,
              change_probability: float,
              num_coefficients: int,
              red:      {magnitude: float,
                         rmse: float,
                         coefficients: (float, float, ...),
                         intercept: float},
              green:    {magnitude: float,
                         rmse: float,
                         coefficients: (float, float, ...),
                         intercept: float},
              blue:     {magnitude: float,
                         rmse: float,
                         coefficients: (float, float, ...),
                         intercept: float},
              nir:      {magnitude: float,
                         rmse: float,
                         coefficients: (float, float, ...),
                         intercept: float},
              swir1:    {magnitude: float,
                         rmse: float,
                         coefficients: (float, float, ...),
                         intercept: float},
              swir2:    {magnitude: float,
                         rmse: float,
                         coefficients: (float, float, ...),
                         intercept: float},
              thermal:  {magnitude: float,
                         rmse: float,
                         coefficients: (float, float, ...),
                         intercept: float}}
                        ]
        }
    """
    spectra = ((defaults.RED_IDX, 'red'), (defaults.GREEN_IDX, 'green'), (defaults.BLUE_IDX, 'blue'),
               (defaults.NIR_IDX, 'nir'), (defaults.SWIR1_IDX, 'swir1'), (defaults.SWIR2_IDX, 'swir2'),
               (defaults.THERMAL_IDX, 'thermal'))

    # get the start and end time for each detection period
    detection = {'algorithm': __algorithm__,
                 'processing_mask': processing_mask,
                 'procedure': procedure.__name__}
    # gather the results for each spectra
    for ix, name in spectra:
        model, error, mags = change_tuple[2], change_tuple[3], change_tuple[4]
        _band = {'magnitude': float(mags[ix]),
                 'rmse': float(error[ix]),
                 'coefficients': tuple([float(x) for x in model[ix].coef_]),
                 'intercept': float(model[ix].intercept_)}

        # assign _band to the subdict
        detection[name] = _band

    # build the namedtuple from the dict and return
    return detection


def __as_detections(detect_tuple):
    """Transforms results of change.detect to the detections namedtuple.

    Args: A tuple of dicts as returned from change.detect
        (
            (start_day, end_day, models, errors_, magnitudes_),
            (start_day, end_day, models, errors_, magnitudes_),
            (start_day, end_day, models, errors_, magnitudes_)
        )

    Returns: A tuple of dicts representing change detections
        (
            {},{},{}}
        )
    """
    # iterate over each detection, build the result and return as tuple of
    # dicts
    return tuple([__result_to_detection(t) for t in detect_tuple])


def __split_dates_spectra(matrix):
    """ Slice the dates and spectra from the matrix and return """
    return matrix[0], matrix[1:7]


def detect(dates, reds, greens, blues, nirs,
           swir1s, swir2s, thermals, quality):
    """Entry point call to detect change

    No filtering up-front as different procedures may do things
    differently

    Args:
        dates:    1d-array or list of ordinal date values
        reds:     1d-array or list of red band values
        greens:   1d-array or list of green band values
        blues:    1d-array or list of blue band values
        nirs:     1d-array or list of nir band values
        swir1s:   1d-array or list of swir1 band values
        swir2s:   1d-array or list of swir2 band values
        thermals: 1d-array or list of thermal band values
        quality:  1d-array or list of qa band values

    Returns:
        Tuple of ccd.detections namedtuples
    """
    dates = np.asarray(dates)

    spectra = np.stack((reds, greens,
                        blues, nirs, swir1s,
                        swir2s, thermals))

    # load the fitter_fn from app.FITTER_FN
    fitter_fn = attr_from_str(defaults.FITTER_FN)

    # Determine which procedure to use for the detection
    procedure = __determine_fit_procedure(quality)

    # call detect and return results as the detections namedtuple
    return __as_detections(procedure(dates, spectra, fitter_fn, quality))
