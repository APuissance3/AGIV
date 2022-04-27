# This Python file uses the following encoding: utf-8


class CCheckRangePoint():
    """ This class could check a measure point using
        yaml_data file to get the tolerances 
    """

    def __init__(self, range_data, mode='') -> None:
        self.percent = range_data['tolerance'][0]
        self.resolution = range_data['tolerance'][1]
        self.full_scale = range_data['points'][-1]  # -1: The last points
        self.fs_mode = True if 'FS' or 'fs' in mode else False

    def calc_val_limits (self, check_valu):
        """ Return the min and max tolered values for the check_value """
        val_percent = check_valu / 100.0 * self.percent
        if self.fs_mode:  # In case of Full scale mode, use the bigest point
            val_percent = self.full_scale / 100.0 * self.percent 
        val_min = check_valu - val_percent - self.resolution
        val_max = check_valu + val_percent +  self.resolution
        return(val_min, val_max)

    def check_val(self, value_in, value_out):
        """ Check if the read_val for check_value is conform to the tolerances """
        (min,max) = self.calc_val_limits(value_in)
        if value_out< min:
            return (False, min, max)
        elif value_out > max:
            return (False, min, max)
        else:
            return (True, min, max)
