from __future__ import division, print_function, absolute_import

import numpy as np
from numpy.testing import (assert_, assert_equal, assert_allclose,
                           assert_almost_equal)  # avoid new uses

import pytest
from pytest import raises as assert_raises
from scipy.stats._hypotests import (epps_singleton_2samp, cramervonmises,
                                    _cdf_cvm, cramervonmises_2samp,
                                    _pval_cvm_2samp_exact)
import scipy.stats as stats
from scipy.stats import distributions
from .common_tests import check_named_results


class TestEppsSingleton(object):
    def test_statistic_1(self):
        # first example in Goerg & Kaiser, also in original paper of
        # Epps & Singleton. Note: values do not match exactly, the
        # value of the interquartile range varies depending on how
        # quantiles are computed
        x = np.array([-0.35, 2.55, 1.73, 0.73, 0.35,
                      2.69, 0.46, -0.94, -0.37, 12.07])
        y = np.array([-1.15, -0.15, 2.48, 3.25, 3.71,
                      4.29, 5.00, 7.74, 8.38, 8.60])
        w, p = epps_singleton_2samp(x, y)
        assert_almost_equal(w, 15.14, decimal=1)
        assert_almost_equal(p, 0.00442, decimal=3)

    def test_statistic_2(self):
        # second example in Goerg & Kaiser, again not a perfect match
        x = np.array((0, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 5, 5, 5, 5, 6, 10,
                      10, 10, 10))
        y = np.array((10, 4, 0, 5, 10, 10, 0, 5, 6, 7, 10, 3, 1, 7, 0, 8, 1,
                      5, 8, 10))
        w, p = epps_singleton_2samp(x, y)
        assert_allclose(w, 8.900, atol=0.001)
        assert_almost_equal(p, 0.06364, decimal=3)

    def test_epps_singleton_array_like(self):
        np.random.seed(1234)
        x, y = np.arange(30), np.arange(28)

        w1, p1 = epps_singleton_2samp(list(x), list(y))
        w2, p2 = epps_singleton_2samp(tuple(x), tuple(y))
        w3, p3 = epps_singleton_2samp(x, y)

        assert_(w1 == w2 == w3)
        assert_(p1 == p2 == p3)

    def test_epps_singleton_size(self):
        # raise error if less than 5 elements
        x, y = (1, 2, 3, 4), np.arange(10)
        assert_raises(ValueError, epps_singleton_2samp, x, y)

    def test_epps_singleton_nonfinite(self):
        # raise error if there are non-finite values
        x, y = (1, 2, 3, 4, 5, np.inf), np.arange(10)
        assert_raises(ValueError, epps_singleton_2samp, x, y)
        x, y = np.arange(10), (1, 2, 3, 4, 5, np.nan)
        assert_raises(ValueError, epps_singleton_2samp, x, y)

    def test_names(self):
        x, y = np.arange(20), np.arange(30)
        res = epps_singleton_2samp(x, y)
        attributes = ('statistic', 'pvalue')
        check_named_results(res, attributes)


class TestCvm(object):
    # the expected values of the cdfs are taken from Table 1 in
    # Csorgo / Faraway: The Exact and Asymptotic Distribution of
    # Cramér-von Mises Statistics, 1996.
    def test_cdf_4(self):
        assert_allclose(
                _cdf_cvm([0.02983, 0.04111, 0.12331, 0.94251], 4),
                [0.01, 0.05, 0.5, 0.999],
                atol=1e-4)

    def test_cdf_10(self):
        assert_allclose(
                _cdf_cvm([0.02657, 0.03830, 0.12068, 0.56643], 10),
                [0.01, 0.05, 0.5, 0.975],
                atol=1e-4)

    def test_cdf_1000(self):
        assert_allclose(
                _cdf_cvm([0.02481, 0.03658, 0.11889, 1.16120], 1000),
                [0.01, 0.05, 0.5, 0.999],
                atol=1e-4)

    def test_cdf_inf(self):
        assert_allclose(
                _cdf_cvm([0.02480, 0.03656, 0.11888, 1.16204]),
                [0.01, 0.05, 0.5, 0.999],
                atol=1e-4)

    def test_cdf_support(self):
        # cdf has support on [1/(12*n), n/3]
        assert_equal(_cdf_cvm([1/(12*533), 533/3], 533), [0, 1])
        assert_equal(_cdf_cvm([1/(12*(27 + 1)), (27 + 1)/3], 27), [0, 1])

    def test_cdf_large_n(self):
        # test that asymptotic cdf and cdf for large samples are close
        assert_allclose(
                _cdf_cvm([0.02480, 0.03656, 0.11888, 1.16204, 100], 10000),
                _cdf_cvm([0.02480, 0.03656, 0.11888, 1.16204, 100]),
                atol=1e-4)

    def test_large_x(self):
        # for large values of x and n, the series used to compute the cdf
        # converges slowly.
        # this leads to bug in R package goftest and MAPLE code that is
        # the basis of the implemenation in scipy
        # note: cdf = 1 for x >= 1000/3 and n = 1000
        assert_(0.99999 < _cdf_cvm(333.3, 1000) < 1.0)
        assert_(0.99999 < _cdf_cvm(333.3) < 1.0)

    def test_low_p(self):
        # _cdf_cvm can return values larger than 1. In that case, we just
        # return a p-value of zero.
        n = 12
        res = cramervonmises(np.ones(n)*0.8, 'norm')
        assert_(_cdf_cvm(res.statistic, n) > 1.0)
        assert_equal(res.pvalue, 0)

    def test_invalid_input(self):
        x = np.arange(10).reshape((2, 5))
        assert_raises(ValueError, cramervonmises, x, "norm")
        assert_raises(ValueError, cramervonmises, [1.5], "norm")
        assert_raises(ValueError, cramervonmises, (), "norm")

    def test_values_R(self):
        # compared against R package goftest, version 1.1.1
        # goftest::cvm.test(c(-1.7, 2, 0, 1.3, 4, 0.1, 0.6), "pnorm")
        res = cramervonmises([-1.7, 2, 0, 1.3, 4, 0.1, 0.6], "norm")
        assert_allclose(res.statistic, 0.288156, atol=1e-6)
        assert_allclose(res.pvalue, 0.1453465, atol=1e-6)

        # goftest::cvm.test(c(-1.7, 2, 0, 1.3, 4, 0.1, 0.6),
        #                   "pnorm", mean = 3, sd = 1.5)
        res = cramervonmises([-1.7, 2, 0, 1.3, 4, 0.1, 0.6], "norm", (3, 1.5))
        assert_allclose(res.statistic, 0.9426685, atol=1e-6)
        assert_allclose(res.pvalue, 0.002026417, atol=1e-6)

        # goftest::cvm.test(c(1, 2, 5, 1.4, 0.14, 11, 13, 0.9, 7.5), "pexp")
        res = cramervonmises([1, 2, 5, 1.4, 0.14, 11, 13, 0.9, 7.5], "expon")
        assert_allclose(res.statistic, 0.8421854, atol=1e-6)
        assert_allclose(res.pvalue, 0.004433406, atol=1e-6)

    def test_callable_cdf(self):
        x, args = np.arange(5), (1.4, 0.7)
        r1 = cramervonmises(x, distributions.expon.cdf)
        r2 = cramervonmises(x, "expon")
        assert_equal((r1.statistic, r1.pvalue), (r2.statistic, r2.pvalue))

        r1 = cramervonmises(x, distributions.beta.cdf, args)
        r2 = cramervonmises(x, "beta", args)
        assert_equal((r1.statistic, r1.pvalue), (r2.statistic, r2.pvalue))


class TestSomersD(object):

    def test_like_kendalltau(self):
        # All tests correspond with one in test_stats.py `test_kendalltau`

        # case without ties, con-dis equal zero
        x = [5, 2, 1, 3, 6, 4, 7, 8]
        y = [5, 2, 6, 3, 1, 8, 7, 4]
        # Cross-check with result from SAS FREQ:
        expected = (0.000000000000000, 1.000000000000000)
        res = stats.somersd(x, y)
        assert_allclose(res.statistic, expected[0], atol=1e-15)
        assert_allclose(res.pvalue, expected[1], atol=1e-15)

        # case without ties, con-dis equal zero
        x = [0, 5, 2, 1, 3, 6, 4, 7, 8]
        y = [5, 2, 0, 6, 3, 1, 8, 7, 4]
        # Cross-check with result from SAS FREQ:
        expected = (0.000000000000000, 1.000000000000000)
        res = stats.somersd(x, y)
        assert_allclose(res.statistic, expected[0], atol=1e-15)
        assert_allclose(res.pvalue, expected[1], atol=1e-15)

        # case without ties, con-dis close to zero
        x = [5, 2, 1, 3, 6, 4, 7]
        y = [5, 2, 6, 3, 1, 7, 4]
        # Cross-check with result from SAS FREQ:
        expected = (-0.142857142857140, 0.630326953157670)
        res = stats.somersd(x, y)
        assert_allclose(res.statistic, expected[0], atol=1e-15)
        assert_allclose(res.pvalue, expected[1], atol=1e-15)

        # simple case without ties
        x = np.arange(10)
        y = np.arange(10)
        # Cross-check with result from SAS FREQ:
        # SAS p value is not provided.
        expected = (1.000000000000000, 0)
        res = stats.somersd(x, y)
        assert_allclose(res.statistic, expected[0], atol=1e-15)
        assert_allclose(res.pvalue, expected[1], atol=1e-15)

        # swap a couple values and a couple more
        x = np.arange(10)
        y = np.array([0, 2, 1, 3, 4, 6, 5, 7, 8, 9])
        # Cross-check with result from SAS FREQ:
        expected = (0.911111111111110, 0.000000000000000)
        res = stats.somersd(x, y)
        assert_allclose(res.statistic, expected[0], atol=1e-15)
        assert_allclose(res.pvalue, expected[1], atol=1e-15)

        # same in opposite direction
        x = np.arange(10)
        y = np.arange(10)[::-1]
        # Cross-check with result from SAS FREQ:
        # SAS p value is not provided.
        expected = (-1.000000000000000, 0)
        res = stats.somersd(x, y)
        assert_allclose(res.statistic, expected[0], atol=1e-15)
        assert_allclose(res.pvalue, expected[1], atol=1e-15)

        # swap a couple values and a couple more
        x = np.arange(10)
        y = np.array([9, 7, 8, 6, 5, 3, 4, 2, 1, 0])
        # Cross-check with result from SAS FREQ:
        expected = (-0.9111111111111111, 0.000000000000000)
        res = stats.somersd(x, y)
        assert_allclose(res.statistic, expected[0], atol=1e-15)
        assert_allclose(res.pvalue, expected[1], atol=1e-15)

        # with some ties
        x1 = [12, 2, 1, 12, 2]
        x2 = [1, 4, 7, 1, 0]
        # Cross-check with result from SAS FREQ:
        expected = (-0.500000000000000, 0.304901788178780)
        res = stats.somersd(x1, x2)
        assert_allclose(res.statistic, expected[0], atol=1e-15)
        assert_allclose(res.pvalue, expected[1], atol=1e-15)

        # with only ties in one or both inputs
        # SAS will not produce an output for these:
        # NOTE: No statistics are computed for x * y because x has fewer
        # than 2 nonmissing levels.
        # WARNING: No OUTPUT data set is produced for this table because a
        # row or column variable has fewer than 2 nonmissing levels and no
        # statistics are computed.

        res = stats.somersd([2, 2, 2], [2, 2, 2])
        assert_allclose(res.statistic, np.nan)
        assert_allclose(res.pvalue, np.nan)

        res = stats.somersd([2, 0, 2], [2, 2, 2])
        assert_allclose(res.statistic, np.nan)
        assert_allclose(res.pvalue, np.nan)

        res = stats.somersd([2, 2, 2], [2, 0, 2])
        assert_allclose(res.statistic, np.nan)
        assert_allclose(res.pvalue, np.nan)

        res = stats.somersd([0], [0])
        assert_allclose(res.statistic, np.nan)
        assert_allclose(res.pvalue, np.nan)

        # empty arrays provided as input
        res = stats.somersd([], [])
        assert_allclose(res.statistic, np.nan)
        assert_allclose(res.pvalue, np.nan)

        # test unequal length inputs
        x = np.arange(10.)
        y = np.arange(20.)
        assert_raises(ValueError, stats.somersd, x, y)

    def test_asymmetry(self):
        # test that somersd is asymmetric w.r.t. input order and that
        # convention is as described: first input is row variable & independent
        # data is from Wikipedia:
        # https://en.wikipedia.org/wiki/Somers%27_D
        # but currently that example contradicts itself - it says X is
        # independent yet take D_XY

        x = [1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 1, 2,
             2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3]
        y = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2,
             2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2]
        # Cross-check with result from SAS FREQ:
        d_cr = 0.272727272727270
        d_rc = 0.342857142857140
        p = 0.092891940883700  # same p-value for either direction
        res = stats.somersd(x, y)
        assert_allclose(res.statistic, d_cr, atol=1e-15)
        assert_allclose(res.pvalue, p, atol=1e-4)
        assert_equal(res.table.shape, (3, 2))
        res = stats.somersd(y, x)
        assert_allclose(res.statistic, d_rc, atol=1e-15)
        assert_allclose(res.pvalue, p, atol=1e-15)
        assert_equal(res.table.shape, (2, 3))

    def test_somers_original(self):
        # test against Somers' original paper [1]

        # Table 5A
        # Somers' convention was column IV
        table = np.array([[8, 2], [6, 5], [3, 4], [1, 3], [2, 3]])
        # Our convention (and that of SAS FREQ) is row IV
        table = table.T
        dyx = 129/340
        assert_allclose(stats.somersd(table).statistic, dyx)

        # table 7A - d_yx = 1
        table = np.array([[25, 0], [85, 0], [0, 30]])
        dxy, dyx = 3300/5425, 3300/3300
        assert_allclose(stats.somersd(table).statistic, dxy)
        assert_allclose(stats.somersd(table.T).statistic, dyx)

        # table 7B - d_yx < 0
        table = np.array([[25, 0], [0, 30], [85, 0]])
        dyx = -1800/3300
        assert_allclose(stats.somersd(table.T).statistic, dyx)

    def test_contingency_table_with_zero_rows_cols(self):
        # test that zero rows/cols in contingency table don't affect result

        N = 100
        shape = 4, 6
        size = np.prod(shape)

        np.random.seed(0)
        s = stats.multinomial.rvs(N, p=np.ones(size)/size).reshape(shape)
        res = stats.somersd(s)

        s2 = np.insert(s, 2, np.zeros(shape[1]), axis=0)
        res2 = stats.somersd(s2)

        s3 = np.insert(s, 2, np.zeros(shape[0]), axis=1)
        res3 = stats.somersd(s3)

        s4 = np.insert(s2, 2, np.zeros(shape[0]+1), axis=1)
        res4 = stats.somersd(s4)

        # Cross-check with result from SAS FREQ:
        assert_allclose(res.statistic, -0.116981132075470, atol=1e-15)
        assert_allclose(res.statistic, res2.statistic)
        assert_allclose(res.statistic, res3.statistic)
        assert_allclose(res.statistic, res4.statistic)

        assert_allclose(res.pvalue, 0.156376448188150, atol=1e-15)
        assert_allclose(res.pvalue, res2.pvalue)
        assert_allclose(res.pvalue, res3.pvalue)
        assert_allclose(res.pvalue, res4.pvalue)

    def test_invalid_contingency_tables(self):
        N = 100
        shape = 4, 6
        size = np.prod(shape)

        np.random.seed(0)
        # start with a valid contingency table
        s = stats.multinomial.rvs(N, p=np.ones(size)/size).reshape(shape)

        s5 = s - 2
        message = "All elements of the contingency table must be non-negative"
        with assert_raises(ValueError, match=message):
            stats.somersd(s5)

        s6 = s + 0.01
        message = "All elements of the contingency table must be integer"
        with assert_raises(ValueError, match=message):
            stats.somersd(s6)

        message = ("At least two elements of the contingency "
                   "table must be nonzero.")
        with assert_raises(ValueError, match=message):
            stats.somersd([[]])

        with assert_raises(ValueError, match=message):
            stats.somersd([[1]])

        s7 = np.zeros((3, 3))
        with assert_raises(ValueError, match=message):
            stats.somersd(s7)

        s7[0, 1] = 1
        with assert_raises(ValueError, match=message):
            stats.somersd(s7)

    def test_only_ranks_matter(self):
        # only ranks of input data should matter
        x = [1, 2, 3]
        x2 = [-1, 2.1, np.inf]
        y = [3, 2, 1]
        y2 = [0, -0.5, -np.inf]
        res = stats.somersd(x, y)
        res2 = stats.somersd(x2, y2)
        assert_equal(res.statistic, res2.statistic)
        assert_equal(res.pvalue, res2.pvalue)

    def test_contingency_table_return(self):
        # check that contingency table is returned
        x = np.arange(10)
        y = np.arange(10)
        res = stats.somersd(x, y)
        assert_equal(res.table, np.eye(10))


vectorization_nanpolicy_cases = [
    (stats.bartlett, tuple(), dict(), 3),
    (stats.levene, tuple(), {'center':'mean', 'proportiontocut':0.025}, 3),
    (stats.pearsonr, tuple(), dict(), 2),
    (stats.ks_2samp, ("less",),
     {"mode": 'asymp'}, 2),
    (stats.ranksums, tuple(), dict(), 2),
    (stats.ansari, tuple(), dict(), 2),
    (stats.brunnermunzel, ("less",),
     {"distribution": 'normal'}, 2),
    (stats.epps_singleton_2samp, ((.35, 0.75),), {}, 2),
    (stats.shapiro, tuple(), dict(), 1),
    (stats.jarque_bera, tuple(), dict(), 1),
    (stats.ks_1samp, (distributions.norm.cdf,),
     {"alternative": "less", "mode": 'asymp'}, 1),
    ]


@pytest.mark.parametrize(("hypotest", "args", "kwds", "nsamp"),
                         vectorization_nanpolicy_cases)
@pytest.mark.parametrize(("nan_policy"), ("propagate", "omit"))
@pytest.mark.parametrize(("axis"), (0, 1))
def test_hypotest_vectorization(hypotest, args, kwds, nsamp, nan_policy, axis):
    # test that hypothesis tests using _vectorize_2s_hypotest_factory decorator
    # vectorize as expected
    m, n = 8, 9

    np.random.seed(0)
    x = np.random.rand(nsamp, m, n)

    if nan_policy == 'omit':
        nan_mask = np.random.rand(m, n) > 0.85
        x[:, nan_mask] = np.nan  # e.g. pearson requires x and y same mask

    # perform test along last axis for each element of second to last axis
    # consider rewriting for arbitrary number of dimensions, though
    x2 = np.moveaxis(x.copy(), axis+1, -1)
    output_size = x2.shape[-2]
    stats, ps = np.zeros(output_size), np.zeros(output_size)
    for i in range(output_size):
        xi = x2[:, i, :]
        if nan_policy == 'omit':
            xi = [xji[~np.isnan(xji)] for xji in xi]
        stats[i], ps[i] = hypotest(*xi, *args, **kwds)
    res = hypotest(*x, axis=axis, nan_policy=nan_policy, *args, **kwds)
    assert_equal(res[0], stats)
    assert_equal(res[1], ps)


@pytest.mark.parametrize(("hypotest", "args", "kwds", "nsamp"),
                         vectorization_nanpolicy_cases)
def test_hypotest_nan_raise(hypotest, args, kwds, nsamp):
    m, n = 8, 9
    np.random.seed(0)
    x = np.random.rand(nsamp, m, n)
    nan_mask = np.random.rand(nsamp, m, n) > 0.85
    x[nan_mask] = np.nan

    with assert_raises(ValueError, match="The input contains nan values"):
        hypotest(*x, nan_policy="raise", *args, **kwds)


# previously,
# pearsonr raised TypeError calling mean
# ranksums produced garbage 1d, as far as I can tell
# ansari produced garbage 1d, as far as I can tell
# brunnermunzel raised ValueError about broadcasting
# epps_singleton_2samp raised error that sample must be 1d
@pytest.mark.parametrize(("hypotest", "nsamp"),
                         [(stats.jarque_bera, 1),
                          (stats.shapiro, 1)])
def test_hypotest_back_compat_no_axis(hypotest, nsamp):
    m, n = 8, 9
    np.random.seed(0)
    x = np.random.rand(nsamp, m, n)
    res = hypotest(*x)
    res2 = hypotest([xi.ravel() for xi in x])
    assert_equal(res, res2)


class TestCvm_2samp(object):
    def test_invalid_input(self):
        x = np.arange(10).reshape((2, 5))
        y = np.arange(5)
        msg = 'The samples must be one-dimensional'
        with pytest.raises(ValueError, match=msg):
            cramervonmises_2samp(x, y)
        with pytest.raises(ValueError, match=msg):
            cramervonmises_2samp(y, x)
        msg = 'x and y must contain at least two observations.'
        with pytest.raises(ValueError, match=msg):
            cramervonmises_2samp([], y)
        with pytest.raises(ValueError, match=msg):
            cramervonmises_2samp(y, [1])
        msg = 'method must be either auto, exact or asymptotic'
        with pytest.raises(ValueError, match=msg):
            cramervonmises_2samp(y, y, 'xyz')

    def test_list_input(self):
        x = [2, 3, 4, 7, 6]
        y = [0.2, 0.7, 12, 18]
        r1 = cramervonmises_2samp(x, y)
        r2 = cramervonmises_2samp(np.array(x), np.array(y))
        assert_equal((r1.statistic, r1.pvalue), (r2.statistic, r2.pvalue))

    def test_example_conover(self):
        # Example 2 in Section 6.2 of W.J. Conover: Practical Nonparametric
        # Statistics, 1971.
        x = [7.6, 8.4, 8.6, 8.7, 9.3, 9.9, 10.1, 10.6, 11.2]
        y = [5.2, 5.7, 5.9, 6.5, 6.8, 8.2, 9.1, 9.8, 10.8, 11.3, 11.5, 12.3,
             12.5, 13.4, 14.6]
        r = cramervonmises_2samp(x, y)
        assert_allclose(r.statistic, 0.262, atol=1e-3)
        assert_allclose(r.pvalue, 0.18, atol=1e-2)

    @pytest.mark.parametrize('statistic, m, n, pval',
                             [(710, 5, 6, 48./462),
                              (1897, 7, 7, 117./1716),
                              (576, 4, 6, 2./210),
                              (1764, 6, 7, 2./1716)])
    def test_exact_pvalue(self, statistic, m, n, pval):
        # the exact values are taken from Anderson: On the distribution of the
        # two-sample Cramer-von-Mises criterion, 1962.
        # The values are taken from Table 2, 3, 4 and 5
        assert_equal(_pval_cvm_2samp_exact(statistic, m, n), pval)

    def test_large_sample(self):
        # for large samples, the statistic U gets very large
        # do a sanity check that p-value is not 0, 1 or nan
        np.random.seed(4367)
        x = distributions.norm.rvs(size=1000000)
        y = distributions.norm.rvs(size=900000)
        r = cramervonmises_2samp(x, y)
        assert_(0 < r.pvalue < 1)
        r = cramervonmises_2samp(x, y+0.1)
        assert_(0 < r.pvalue < 1)

    def test_exact_vs_asymptotic(self):
        np.random.seed(0)
        x = np.random.rand(7)
        y = np.random.rand(8)
        r1 = cramervonmises_2samp(x, y, method='exact')
        r2 = cramervonmises_2samp(x, y, method='asymptotic')
        assert_equal(r1.statistic, r2.statistic)
        assert_allclose(r1.pvalue, r2.pvalue, atol=1e-2)

    #@pytest.mark.slow
    def test_method_auto(self):
        x = np.arange(10)
        y = [0.5, 4.7, 13.1]
        r1 = cramervonmises_2samp(x, y, method='exact')
        r2 = cramervonmises_2samp(x, y, method='auto')
        assert_equal(r1.pvalue, r2.pvalue)
        # switch to asymptotic if one sample has more than 10 observations
        x = np.arange(11)
        r1 = cramervonmises_2samp(x, y, method='asymptotic')
        r2 = cramervonmises_2samp(x, y, method='auto')
        assert_equal(r1.pvalue, r2.pvalue)

    def test_same_input(self):
        # make sure trivial edge case can be handled
        # note that _cdf_cvm_inf(0) = nan. implementation avoids nan by
        # returning pvalue=1 for very small values of the statistic
        x = np.arange(15)
        res = cramervonmises_2samp(x, x)
        assert_equal((res.statistic, res.pvalue), (0.0, 1.0))
        # check exact p-value
        res = cramervonmises_2samp(x[:4], x[:4])
        assert_equal((res.statistic, res.pvalue), (0.0, 1.0))
