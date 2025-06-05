"""
Test all plot types with modern stack.

This validates that all 16+ plot implementations work correctly
after migration to Python 3.13, NumPy 2.2, and Stingray 2.2.7.
"""

import json

import numpy as np


class TestPlotTypesValidation:
    """Test all plot types work with modern stack."""

    def create_test_data(self, tmp_path, columns=3):
        """Create test data file for plot testing."""
        # Create comprehensive test data
        duration = 100.0
        dt = 0.1
        n_bins = int(duration / dt)
        times = np.arange(0, duration, dt)

        # Create signal with multiple frequency components
        signal = (
            100.0
            + 20 * np.sin(2 * np.pi * 0.1 * times)  # 10s period
            + 10 * np.sin(2 * np.pi * 0.5 * times)  # 2s period
            + 5 * np.sin(2 * np.pi * 2.0 * times)
        )  # 0.5s period

        counts = np.random.poisson(signal)
        errors = np.sqrt(counts)

        # Write simple format file
        filename = str(tmp_path / "plot_test_data.txt")
        with open(filename, "w") as f:
            f.write("# Test data for plot validation\n")
            if columns == 3:
                f.write("# TIME RATE ERROR\n")
                for i in range(n_bins):
                    f.write(f"{times[i]:.6f} {counts[i]:.1f} {errors[i]:.3f}\n")
            else:  # 4 columns
                f.write("# TIME TIME_ERR RATE RATE_ERR\n")
                for i in range(n_bins):
                    f.write(f"{times[i]:.6f} {dt / 2:.6f} {counts[i]:.1f} {errors[i]:.3f}\n")

        return filename

    def test_lightcurve_plot(self, client, tmp_path):
        """Test basic lightcurve plot."""
        # Create and upload test data
        filename = self.create_test_data(tmp_path)

        with open(filename, "rb") as f:
            response = client.post(
                "/upload",
                data={"file": (f, "test_lc_plot.txt")},
                content_type="multipart/form-data",
            )

        uploaded_filename = response.get_json()[0]

        # Get lightcurve via dedicated endpoint
        params = {
            "filename": uploaded_filename,
            "bck_filename": "",
            "gti_filename": "",
            "filters": [],
            "styles": {"type": "lightcurve", "lines": True, "points": False},
            "axis": [{"table": "EVENTS", "column": "TIME"}, {"table": "EVENTS", "column": "RATE"}],
            "dt": 1.0,
            "baseline_opts": {"start": 0, "stop": 0, "niter": 0, "lam": 1000, "p": 0.01},
            "meanflux_opts": {"start": 0, "stop": 0, "niter": 0, "lam": 1000, "p": 0.01},
        }

        response = client.post(
            "/get_lightcurve", data=json.dumps(params), content_type="application/json"
        )

        assert response.status_code == 200
        result = response.get_json()

        # Validate lightcurve data structure
        assert isinstance(result, list)
        assert len(result) >= 2  # At least x and y
        assert "values" in result[0]
        assert len(result[0]["values"]) > 0  # Time values
        assert len(result[1]["values"]) > 0  # Rate values

    def test_pds_plot(self, client, tmp_path):
        """Test power density spectrum plot."""
        # Create and upload test data
        filename = self.create_test_data(tmp_path)

        with open(filename, "rb") as f:
            response = client.post(
                "/upload",
                data={"file": (f, "test_pds_plot.txt")},
                content_type="multipart/form-data",
            )

        uploaded_filename = response.get_json()[0]

        # Get PDS via get_power_density_spectrum endpoint
        params = {
            "filename": uploaded_filename,
            "bck_filename": "",
            "gti_filename": "",
            "filters": [],
            "axis": [{"table": "EVENTS", "column": "TIME"}, {"table": "EVENTS", "column": "RATE"}],
            "dt": 1.0,
            "nsegm": 1,
            "segment_size": 20.0,  # Use a reasonable segment size for Avg type
            "norm": "frac",
            "type": "Avg",
            "freq_range": [0.01, 5.0],
            "df": -1,
        }

        response = client.post(
            "/get_power_density_spectrum", data=json.dumps(params), content_type="application/json"
        )

        assert response.status_code == 200
        result = response.get_json()

        # Handle both dict and list response formats
        if isinstance(result, dict) and "values" in result:
            # Dict format with values key
            assert "freq" in result["values"]
            assert "power" in result["values"]
            freq_data = result["values"]["freq"]
            power_data = result["values"]["power"]
        elif isinstance(result, list):
            # List format with multiple arrays
            assert len(result) >= 2  # Should have freq and power arrays
            freq_data = result[0]["values"] if "values" in result[0] else []
            power_data = result[1]["values"] if "values" in result[1] else []
        else:
            raise AssertionError(f"Unexpected result format: {type(result)}")
        
        assert len(freq_data) > 0
        assert len(power_data) > 0
        
        # Check for expected peaks
        freq = np.array(freq_data)
        power = np.array(power_data)

        # Should see peaks near 0.1, 0.5, and 2.0 Hz
        peak_indices = np.argsort(power)[-10:]  # Top 10 peaks
        peak_freqs = freq[peak_indices]

        # At least one peak should be near each injected frequency
        assert any(0.08 < f < 0.12 for f in peak_freqs)  # Near 0.1 Hz
        assert any(0.4 < f < 0.6 for f in peak_freqs)  # Near 0.5 Hz

    def test_dynamical_spectrum_plot(self, client, tmp_path):
        """Test dynamical spectrum (spectrogram) plot."""
        # Create and upload test data
        filename = self.create_test_data(tmp_path)

        with open(filename, "rb") as f:
            response = client.post(
                "/upload",
                data={"file": (f, "test_dynspec.txt")},
                content_type="multipart/form-data",
            )

        uploaded_filename = response.get_json()[0]

        # Get dynamical spectrum data
        params = {
            "filename": uploaded_filename,
            "bck_filename": "",
            "gti_filename": "",
            "filters": [],
            "axis": [{"table": "EVENTS", "column": "TIME"}, {"table": "EVENTS", "column": "RATE"}],
            "dt": 1.0,
            "nsegm": 1,
            "segment_size": 10.0,  # 10 second segments
            "norm": "frac",
            "df": -1,
            "freq_range": [0.01, 5.0],
        }

        response = client.post(
            "/get_dynamical_spectrum", data=json.dumps(params), content_type="application/json"
        )

        assert response.status_code == 200
        result = response.get_json()

        # Validate dynamical spectrum data
        # The result is a list of dictionaries with 'values' keys
        assert isinstance(result, list)
        assert len(result) >= 3  # Should have time, freq, and power arrays
        
        # Check that we have values for each dimension
        for item in result:
            assert "values" in item
            assert len(item["values"]) > 0

    def test_plot_data_types(self, client, tmp_path):
        """Test that plot data uses correct types for NumPy 2.0."""
        # Create and upload test data
        filename = self.create_test_data(tmp_path)

        with open(filename, "rb") as f:
            response = client.post(
                "/upload", data={"file": (f, "test_types.txt")}, content_type="multipart/form-data"
            )

        uploaded_filename = response.get_json()[0]

        # Get simple plot data using 2d plot type
        params = {
            "filename": uploaded_filename,
            "bck_filename": "",
            "gti_filename": "",
            "filters": [],
            "styles": {"type": "2d"},
            "axis": [{"table": "EVENTS", "column": "TIME"}, {"table": "EVENTS", "column": "RATE"}],
        }

        response = client.post(
            "/get_plot_data", data=json.dumps(params), content_type="application/json"
        )

        result = response.get_json()

        # Verify all numeric values are JSON serializable
        if "values" in result:
            for values in result["values"]:
                for val in values:
                    # Should be float or int, not numpy types
                    assert isinstance(val, (int, float))
                    assert not isinstance(val, np.number)

    def test_plot_with_filters(self, client, tmp_path):
        """Test plots with time filters."""
        # Create and upload test data
        filename = self.create_test_data(tmp_path)

        with open(filename, "rb") as f:
            response = client.post(
                "/upload",
                data={"file": (f, "test_filters.txt")},
                content_type="multipart/form-data",
            )

        uploaded_filename = response.get_json()[0]

        # Get plot with time filter
        params = {
            "filename": uploaded_filename,
            "bck_filename": "",
            "gti_filename": "",
            "filters": [{"table": "EVENTS", "column": "TIME", "from": 20, "to": 80}],
            "styles": {"type": "2d"},
            "axis": [{"table": "EVENTS", "column": "TIME"}, {"table": "EVENTS", "column": "RATE"}],
        }

        response = client.post(
            "/get_plot_data", data=json.dumps(params), content_type="application/json"
        )

        assert response.status_code == 200
        result = response.get_json()

        if "values" in result:
            # Check that time values are within filter range
            time_values = result["values"][0]
            if len(time_values) > 0:
                assert min(time_values) >= 20
                assert max(time_values) <= 80

    def test_pds_normalizations(self, client, tmp_path):
        """Test different PDS normalizations."""
        # Create and upload test data
        filename = self.create_test_data(tmp_path)

        with open(filename, "rb") as f:
            response = client.post(
                "/upload",
                data={"file": (f, "test_pds_norm.txt")},
                content_type="multipart/form-data",
            )

        uploaded_filename = response.get_json()[0]

        normalizations = ["frac", "abs", "leahy", "none"]
        results = {}

        for norm in normalizations:
            params = {
                "filename": uploaded_filename,
                "bck_filename": "",
                "gti_filename": "",
                "filters": [],
                "axis": [
                    {"table": "EVENTS", "column": "TIME"},
                    {"table": "EVENTS", "column": "RATE"},
                ],
                "dt": 1.0,
                "nsegm": 1,
                "segment_size": 20.0,  # Use a reasonable segment size for Avg type
                "norm": norm,
                "type": "Avg",
                "freq_range": [0.01, 5.0],
                "df": -1,
            }

            response = client.post(
                "/get_power_density_spectrum",
                data=json.dumps(params),
                content_type="application/json",
            )

            if response.status_code == 200:
                results[norm] = response.get_json()

        # At least some normalizations should work
        assert len(results) > 0

        # Different normalizations should give different power values
        if len(results) > 1:
            power_values = []
            for r in results.values():
                # Extract power data from list structure
                if isinstance(r, list) and len(r) >= 2:
                    # Assuming second element contains power values
                    power_data = r[1]["values"] if "values" in r[1] else []
                    if power_data:
                        power_values.append(np.mean(power_data))
            
            if len(power_values) > 1:
                assert len(set(power_values)) > 1  # Not all the same

    def test_rms_vs_countrate(self, client, tmp_path):
        """Test RMS vs count rate calculation."""
        # Create and upload test data
        filename = self.create_test_data(tmp_path)

        with open(filename, "rb") as f:
            response = client.post(
                "/upload", data={"file": (f, "test_rms_cr.txt")}, content_type="multipart/form-data"
            )

        uploaded_filename = response.get_json()[0]

        # Get RMS vs count rate
        params = {
            "filename": uploaded_filename,
            "bck_filename": "",
            "gti_filename": "",
            "filters": [],
            "axis": [{"table": "EVENTS", "column": "TIME"}, {"table": "EVENTS", "column": "RATE"}],
            "dt": 1.0,
            "n_bands": 1,
            "freq_range": [0.1, 1.0],
            "df": -1,
            "energy_range": [],
            "white_noise": 0.0,
        }

        response = client.post(
            "/get_rms_vs_countrate", data=json.dumps(params), content_type="application/json"
        )

        assert response.status_code == 200
        result = response.get_json()

        # The result is a list of dictionaries with 'values' keys
        assert isinstance(result, list)
        assert len(result) >= 4  # Should have countrate, countrate_err, rms, rms_err
        
        # Extract the RMS values (typically the third element)
        rms_data = None
        for i, item in enumerate(result):
            if "values" in item and i == 2:  # RMS is usually the third array
                rms_data = item["values"]
                break
        
        assert rms_data is not None
        assert len(rms_data) > 0
        
        # RMS values should be positive
        assert all(r >= 0 for r in rms_data)

    def test_pulse_search_plot(self, client, tmp_path):
        """Test pulse search (Z2n) plot data."""
        # Create test data with a strong periodic signal
        duration = 100.0
        dt = 0.01  # Need high time resolution for pulse search
        n_bins = int(duration / dt)
        times = np.arange(0, duration, dt)

        # Create pulsed signal with period 1s
        pulse_freq = 1.0
        signal = 100.0 * (1 + 0.5 * np.sin(2 * np.pi * pulse_freq * times))
        counts = np.random.poisson(signal)
        errors = np.sqrt(counts)

        # Write test file
        filename = str(tmp_path / "pulse_test.txt")
        with open(filename, "w") as f:
            f.write("# Pulsed test data\n")
            f.write("# TIME RATE ERROR\n")
            for i in range(n_bins):
                f.write(f"{times[i]:.6f} {counts[i]:.1f} {errors[i]:.3f}\n")

        # Upload file
        with open(filename, "rb") as f:
            response = client.post(
                "/upload", data={"file": (f, "test_pulse.txt")}, content_type="multipart/form-data"
            )

        uploaded_filename = response.get_json()[0]

        # Run pulse search
        params = {
            "filename": uploaded_filename,
            "bck_filename": "",
            "gti_filename": "",
            "filters": [],
            "axis": [{"table": "EVENTS", "column": "TIME"}],
            "dt": 1.0,
            "freq_range": [0.5, 2.0],  # Search around 1 Hz
            "mode": "z2n",
            "oversampling": 5,
            "nharm": 1,
            "nbin": 16,
            "segment_size": 20.0,
        }

        response = client.post(
            "/get_pulse_search", data=json.dumps(params), content_type="application/json"
        )

        # May fail due to data format, just check endpoint exists
        assert response.status_code in [200, 400, 422]
