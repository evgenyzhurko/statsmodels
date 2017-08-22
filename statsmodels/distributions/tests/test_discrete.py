import os
import numpy as np
import statsmodels.api as sm
from scipy.stats import poisson, nbinom
from numpy.testing import (assert_, assert_raises, assert_almost_equal,
                           assert_equal, assert_array_equal, assert_allclose,
                           assert_array_less)

class TestGenpoisson_p(object):
    """
    Test Generalized Poisson Destribution
    """

    def test_pmf_p1(self):
        poisson_pmf = poisson.pmf(1, 1)
        genpoisson_pmf = sm.distributions.genpoisson_p.pmf(1, 1, 0, 1)
        assert_allclose(poisson_pmf, genpoisson_pmf, rtol=1e-15)

    def test_pmf_p2(self):
        poisson_pmf = poisson.pmf(2, 2)
        genpoisson_pmf = sm.distributions.genpoisson_p.pmf(2, 2, 0, 2)
        assert_allclose(poisson_pmf, genpoisson_pmf, rtol=1e-15)

    def test_pmf_p5(self):
        poisson_pmf = poisson.pmf(10, 2)
        genpoisson_pmf_5 = sm.distributions.genpoisson_p.pmf(10, 2, 1e-25, 5)
        assert_allclose(poisson_pmf, genpoisson_pmf_5, rtol=1e-12)

    def test_logpmf_p1(self):
        poisson_pmf = poisson.logpmf(5, 2)
        genpoisson_pmf = sm.distributions.genpoisson_p.logpmf(5, 2, 0, 1)
        assert_allclose(poisson_pmf, genpoisson_pmf, rtol=1e-15)

    def test_logpmf_p2(self):
        poisson_pmf = poisson.logpmf(6, 1)
        genpoisson_pmf = sm.distributions.genpoisson_p.logpmf(6, 1, 0, 2)
        assert_allclose(poisson_pmf, genpoisson_pmf, rtol=1e-15)

class TestTruncatedPoisson(object):
    """
    Test Truncated Poisson distribution
    """
    def test_pmf_zero(self):
        poisson_pmf = poisson.pmf(100, 100)
        tpoisson_pmf = sm.distributions.truncatedpoisson.pmf(100, 100, 0)
        assert_allclose(poisson_pmf, tpoisson_pmf, rtol=1e-7)

    def test_logpmf_zero(self):
        poisson_logpmf = poisson.logpmf(100, 100)
        tpoisson_logpmf = sm.distributions.truncatedpoisson.logpmf(100, 100, 0)
        assert_allclose(poisson_logpmf, tpoisson_logpmf, rtol=1e-7)

    def test_pmf(self):
        poisson_pmf = poisson.pmf(1, 1)
        tpoisson_pmf = sm.distributions.truncatedpoisson.pmf(1, 1, 50)
        assert_allclose(poisson_pmf, tpoisson_pmf, rtol=1e-7)

    def test_logpmf(self):
        poisson_logpmf = poisson.logpmf(1, 1)
        tpoisson_logpmf = sm.distributions.truncatedpoisson.logpmf(1, 1, 50)
        assert_allclose(poisson_logpmf, tpoisson_logpmf, rtol=1e-7)

class TestTruncatedNBP(object):
    """
    Test Truncated Poisson distribution
    """
    def test_pmf_zero(self):
        n, p = sm.distributions.truncatednegbin.convert_params(30, 0.1, 2)
        nb_pmf = nbinom.pmf(100, n, p)
        tnb_pmf = sm.distributions.truncatednegbin.pmf(100, 30, 0.1, 2, 0)
        assert_allclose(nb_pmf, tnb_pmf, rtol=1e-5)

    def test_logpmf_zero(self):
        n, p = sm.distributions.truncatednegbin.convert_params(10, 1, 2)
        nb_logpmf = nbinom.logpmf(200, n, p)
        tnb_logpmf = sm.distributions.truncatednegbin.logpmf(200, 10, 1, 2, 0)
        assert_allclose(nb_logpmf, tnb_logpmf, rtol=1e-2, atol=1e-2)

    def test_pmf(self):
        n, p = sm.distributions.truncatednegbin.convert_params(2, 0.5, 2)
        nb_logpmf = nbinom.pmf(2, n, p)
        tnb_pmf = sm.distributions.truncatednegbin.pmf(2, 2, 0.5, 2, 50)
        assert_allclose(nb_logpmf, tnb_pmf, rtol=1e-7)

    def test_logpmf(self):
        n, p = sm.distributions.truncatednegbin.convert_params(5, 0.1, 2)
        nb_logpmf = nbinom.logpmf(1, n, p)
        tnb_logpmf = sm.distributions.truncatednegbin.logpmf(1, 5, 0.1, 2, 50)
        assert_allclose(nb_logpmf, tnb_logpmf, rtol=1e-7)

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, '-vvs', '-x', '--pdb'])
