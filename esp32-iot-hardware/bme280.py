import time


class BME280:
    def __init__(self, i2c, address=0x76):
        self.i2c = i2c
        self.address = address

        chip_id = self.i2c.readfrom_mem(self.address, 0xD0, 1)[0]
        if chip_id != 0x60:
            raise OSError("BME280 nicht gefunden an Adresse 0x%02X" % self.address)

        self._load_calibration()

        self.i2c.writeto_mem(self.address, 0xF2, b"\x01")  # humidity oversampling x1
        self.i2c.writeto_mem(self.address, 0xF4, b"\x27")  # temp/pressure oversampling x1, normal mode
        self.i2c.writeto_mem(self.address, 0xF5, b"\xA0")  # standby/filter

        time.sleep_ms(100)

    def _read_u8(self, register):
        return self.i2c.readfrom_mem(self.address, register, 1)[0]

    def _read_s8(self, register):
        value = self._read_u8(register)
        return value - 256 if value > 127 else value

    def _read_u16_le(self, register):
        data = self.i2c.readfrom_mem(self.address, register, 2)
        return data[0] | (data[1] << 8)

    def _read_s16_le(self, register):
        value = self._read_u16_le(register)
        return value - 65536 if value > 32767 else value

    def _load_calibration(self):
        self.dig_T1 = self._read_u16_le(0x88)
        self.dig_T2 = self._read_s16_le(0x8A)
        self.dig_T3 = self._read_s16_le(0x8C)

        self.dig_P1 = self._read_u16_le(0x8E)
        self.dig_P2 = self._read_s16_le(0x90)
        self.dig_P3 = self._read_s16_le(0x92)
        self.dig_P4 = self._read_s16_le(0x94)
        self.dig_P5 = self._read_s16_le(0x96)
        self.dig_P6 = self._read_s16_le(0x98)
        self.dig_P7 = self._read_s16_le(0x9A)
        self.dig_P8 = self._read_s16_le(0x9C)
        self.dig_P9 = self._read_s16_le(0x9E)

        self.dig_H1 = self._read_u8(0xA1)
        self.dig_H2 = self._read_s16_le(0xE1)
        self.dig_H3 = self._read_u8(0xE3)

        e4 = self._read_u8(0xE4)
        e5 = self._read_u8(0xE5)
        e6 = self._read_u8(0xE6)

        self.dig_H4 = (e4 << 4) | (e5 & 0x0F)
        if self.dig_H4 > 2047:
            self.dig_H4 -= 4096

        self.dig_H5 = (e6 << 4) | (e5 >> 4)
        if self.dig_H5 > 2047:
            self.dig_H5 -= 4096

        self.dig_H6 = self._read_s8(0xE7)

    def read_compensated_data(self):
        data = self.i2c.readfrom_mem(self.address, 0xF7, 8)

        adc_p = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
        adc_t = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)
        adc_h = (data[6] << 8) | data[7]

        temperature, t_fine = self._compensate_temperature(adc_t)
        pressure = self._compensate_pressure(adc_p, t_fine)
        humidity = self._compensate_humidity(adc_h, t_fine)

        return temperature, pressure, humidity

    def _compensate_temperature(self, adc_t):
        var1 = (((adc_t >> 3) - (self.dig_T1 << 1)) * self.dig_T2) >> 11
        var2 = (((((adc_t >> 4) - self.dig_T1) * ((adc_t >> 4) - self.dig_T1)) >> 12) * self.dig_T3) >> 14
        t_fine = var1 + var2
        temperature = ((t_fine * 5 + 128) >> 8) / 100
        return temperature, t_fine

    def _compensate_pressure(self, adc_p, t_fine):
        var1 = t_fine - 128000
        var2 = var1 * var1 * self.dig_P6
        var2 = var2 + ((var1 * self.dig_P5) << 17)
        var2 = var2 + (self.dig_P4 << 35)
        var1 = ((var1 * var1 * self.dig_P3) >> 8) + ((var1 * self.dig_P2) << 12)
        var1 = (((1 << 47) + var1) * self.dig_P1) >> 33

        if var1 == 0:
            return 0

        pressure = 1048576 - adc_p
        pressure = (((pressure << 31) - var2) * 3125) // var1
        var1 = (self.dig_P9 * (pressure >> 13) * (pressure >> 13)) >> 25
        var2 = (self.dig_P8 * pressure) >> 19
        pressure = ((pressure + var1 + var2) >> 8) + (self.dig_P7 << 4)

        return pressure / 256

    def _compensate_humidity(self, adc_h, t_fine):
        humidity = t_fine - 76800
        humidity = (((((adc_h << 14) - (self.dig_H4 << 20) - (self.dig_H5 * humidity)) + 16384) >> 15) *
                    (((((((humidity * self.dig_H6) >> 10) * (((humidity * self.dig_H3) >> 11) + 32768)) >> 10) + 2097152) *
                      self.dig_H2 + 8192) >> 14))
        humidity = humidity - (((((humidity >> 15) * (humidity >> 15)) >> 7) * self.dig_H1) >> 4)

        if humidity < 0:
            humidity = 0
        if humidity > 419430400:
            humidity = 419430400

        return (humidity >> 12) / 1024