from __future__ import division

__all__ = ["PoissonZeroInflated"]

import numpy as np
import statsmodels.base.model as base
import statsmodels.base.wrapper as wrap
import statsmodels.regression.linear_model as lm
from statsmodels.discrete.discrete_model import (DiscreteModel, CountModel,
                                                 Poisson, Logit, CountResults,
                                                 L1CountResults,
                                                 _discrete_results_docs)
from statsmodels.distributions import zipoisson
from statsmodels.tools.numdiff import (approx_fprime, approx_hess,
                                       approx_hess_cs, approx_fprime_cs)

class GenericZeroInflated(CountModel):
    __doc__ = """
    Generiz Zero Inflated model for count data

    %(params)s
    %(extra_params)s

    Attributes
    -----------
    endog : array
        A reference to the endogenous response variable
    exog : array
        A reference to the exogenous design.
    exog_infl: array
        A reference to the zero-inflated exogenous design.
    """ % {'params' : base._model_params_doc,
           'extra_params' :
           """offset : array_like
        Offset is added to the linear prediction with coefficient equal to 1.
    exposure : array_like
        Log(exposure) is added to the linear prediction with coefficient
        equal to 1.

    """ + base._missing_param_doc}
    def __init__(self, endog, exog, exog_infl=None, offset=None,
                       exposure=None, missing='none', **kwargs):
        super(GenericZeroInflated, self).__init__(endog, exog, offset=offset,
                                                  exposure=exposure,
                                                  missing=missing, **kwargs)

        if exog_infl is None:
            self.k_inflate = 1
            self.exog_infl = np.ones((endog.size, self.k_inflate))
        else:
            self.exog_infl = exog_infl
            self.k_inflate = exog_infl.shape[1]

        if len(exog.shape) == 1:
            self.k_exog = 1
        else:
            self.k_exog = exog.shape[1]

    def loglike(self, params):
        """
        Loglikelihood of Generic Zero Inflated model

        Parameters
        ----------
        params : array-like
            The parameters of the model.

        Returns
        -------
        loglike : float
            The log-likelihood function of the model evaluated at `params`.
            See notes.

        Notes
        --------
        .. math:: \\ln L=\\sum_{y_{i}=0}\\ln(w_{i}+(1-w_{i})*P_{main\\_model})+
            \\sum_{y_{i}>0}(\\ln(1-w_{i})+L_{main\\_model})
            where P - pdf of main model, L - loglike function of main model.

        """
        return np.sum(self.loglikeobs(params))

    def loglikeobs(self, params):
        """
        Loglikelihood for observations of Generic Zero Inflated model

        Parameters
        ----------
        params : array-like
            The parameters of the model.

        Returns
        -------
        loglike : ndarray (nobs,)
            The log likelihood for each observation of the model evaluated
            at `params`. See Notes

        Notes
        --------
        .. math:: \\ln L=\\ln(w_{i}+(1-w_{i})*P_{main\\_model})+
            \\ln(1-w_{i})+L_{main\\_model}
            where P - pdf of main model, L - loglike function of main model.

        for observations :math:`i=1,...,n`

        """
        params_infl = params[:self.k_inflate]
        params_main = params[self.k_inflate:]

        y = self.endog
        w = self.model_infl.predict(params_infl)
        w[w >= 1.] = np.nextafter(1, 0)
        llf_main = self.model_main.loglikeobs(params_main)
        zero_idx = np.nonzero(y == 0)[0]
        nonzero_idx = np.nonzero(y)[0]

        llf = np.zeros_like(y)
        llf[zero_idx] = (np.log(w[zero_idx] +
            (1 - w[zero_idx]) * np.exp(llf_main[zero_idx])))
        llf[nonzero_idx] = np.log(1 - w[nonzero_idx]) + llf_main[nonzero_idx]

        return llf

    def fit(self, start_params=None, method='bfgs', maxiter=35,
            full_output=1, disp=1, callback=None,
            cov_type='nonrobust', cov_kwds=None, use_t=None, **kwargs):
        if start_params is None:
            offset = getattr(self, "offset", 0) + getattr(self, "exposure", 0)
            if np.size(offset) == 1 and offset == 0:
                offset = None
            mod_poi = Poisson(self.endog, self.exog, offset=offset)
            start_params = mod_poi.fit(disp=0).params
            start_params = np.append(np.zeros(self.k_inflate), start_params)
        mlefit = super(GenericZeroInflated, self).fit(start_params=start_params,
                        maxiter=maxiter, disp=disp,
                        full_output=full_output, callback=lambda x:x,
                        **kwargs)

        zipfit = self.result(self, mlefit._results)
        result = self.result_wrapper(zipfit)

        if cov_kwds is None:
            cov_kwds = {}

        result._get_robustcov_results(cov_type=cov_type,
                                      use_self=True, use_t=use_t, **cov_kwds)
        return result

    fit.__doc__ = DiscreteModel.fit.__doc__

    def fit_regularized(self, start_params=None, method='l1',
            maxiter='defined_by_method', full_output=1, disp=1, callback=None,
            alpha=0, trim_mode='auto', auto_trim_tol=0.01, size_trim_tol=1e-4,
            qc_tol=0.03, **kwargs):
        if start_params is None:
            offset = getattr(self, "offset", 0) + getattr(self, "exposure", 0)
            if np.size(offset) == 1 and offset == 0:
                offset = None
            mod_poi = Poisson(self.endog, self.exog, offset=offset)
            start_params = mod_poi.fit_regularized(
                start_params=start_params, method=method, maxiter=maxiter,
                full_output=full_output, disp=0, callback=callback,
                alpha=alpha_p, trim_mode=trim_mode, auto_trim_tol=auto_trim_tol,
                size_trim_tol=size_trim_tol, qc_tol=qc_tol, **kwargs).params
            start_params = np.append(start_params, 0.1)
        cntfit = super(CountModel, self).fit_regularized(
                start_params=start_params, method=method, maxiter=maxiter,
                full_output=full_output, disp=disp, callback=callback,
                alpha=alpha, trim_mode=trim_mode, auto_trim_tol=auto_trim_tol,
                size_trim_tol=size_trim_tol, qc_tol=qc_tol, **kwargs)

        if method in ['l1', 'l1_cvxopt_cp']:
            discretefit = self.result_reg(self, cntfit)
        else:
            raise Exception(
                    "argument method == %s, which is not handled" % method)

        return self.result_reg_wrapper(discretefit)

    fit_regularized.__doc__ = DiscreteModel.fit_regularized.__doc__

    def score(self, params):
        """
        Generic Zero Inflated model score (gradient) vector of the log-likelihood

        Parameters
        ----------
        params : array-like
            The parameters of the model

        Returns
        -------
        score : ndarray, 1-D
            The score vector of the model, i.e. the first derivative of the
            loglikelihood function, evaluated at `params`
        """
        params_infl = params[:self.k_inflate]
        params_main = params[self.k_inflate:]

        y = self.endog
        w = self.model_infl.predict(params_infl)
        w[w == 1.] = np.nextafter(1, 0)
        score_main = self.model_main.score_obs(params_main)
        llf_main = self.model_main.loglikeobs(params_main)
        llf = self.loglikeobs(params)
        zero_idx = np.nonzero(y == 0)[0]
        nonzero_idx = np.nonzero(y)[0]

        mu = self.model_main.predict(params_main)

        coeff = (1 + w[zero_idx] * (np.exp(mu[zero_idx]) - 1))
        dldp_zero = (score_main[zero_idx].T *
                     (1 - (w[zero_idx]) / np.exp(llf[zero_idx]))).T.sum(0)
        dldp_nonzero = score_main[nonzero_idx].sum(0)
        dldp = dldp_zero + dldp_nonzero

        dldw_zero =  self.exog_infl[zero_idx].T.dot(w[zero_idx] *
            (1 - w[zero_idx]) * (1 - np.exp(llf_main[zero_idx])) / np.exp(llf[zero_idx]))
        dldw_nonzero = -self.exog_infl[nonzero_idx].T.dot(w[nonzero_idx])
        dldw = dldw_zero + dldw_nonzero

        return np.concatenate((dldw, dldp))

    def hessian(self, params):
        """
        Generic Zero Inflated model Hessian matrix of the loglikelihood

        Parameters
        ----------
        params : array-like
            The parameters of the model

        Returns
        -------
        hess : ndarray, (k_vars, k_vars)
            The Hessian, second derivative of loglikelihood function,
            evaluated at `params`

        Notes
        -----
        """
        return approx_hess(params, self.loglike)

class PoissonZeroInflated(GenericZeroInflated):
    """
    Poisson Zero Inflated model for count data

    %(params)s
    %(extra_params)s

    Attributes
    -----------
    endog : array
        A reference to the endogenous response variable
    exog : array
        A reference to the exogenous design.
    exog_infl: array
        A reference to the zero-inflated exogenous design.
    """ % {'params' : base._model_params_doc,
           'extra_params' :
           """offset : array_like
        Offset is added to the linear prediction with coefficient equal to 1.
    exposure : array_like
        Log(exposure) is added to the linear prediction with coefficient
        equal to 1.

    """ + base._missing_param_doc}
    def __init__(self, endog, exog, exog_infl=None, offset=None,
                       exposure=None, missing='none', **kwargs):
        super(PoissonZeroInflated, self).__init__(endog, exog, offset=offset,
                                                  exog_infl=exog_infl,
                                                  exposure=exposure,
                                                  missing=missing, **kwargs)
        self.model_main = Poisson(self.endog, self.exog)
        self.model_infl = Logit(np.zeros(self.exog_infl.shape[0]),
                                self.exog_infl)
        self.result = ZeroInflatedPoissonResults
        self.result_wrapper = ZeroInflatedPoissonResultsWrapper
        self.result_reg = L1ZeroInflatedPoissonResults
        self.result_reg_wrapper = L1ZeroInflatedPoissonResultsWrapper

    def hessian(self, params):
        params_infl = params[:self.k_inflate]
        params_main = params[self.k_inflate:]

        y = self.endog
        w = self.model_infl.predict(params_infl)
        w[w == 1.] = np.nextafter(1, 0)
        score = self.score(params)
        zero_idx = np.nonzero(y == 0)[0]
        nonzero_idx = np.nonzero(y)[0]

        mu = self.model_main.predict(params_main)

        dim = self.k_exog + self.k_inflate

        hess_arr = np.zeros((dim,dim))

        coeff = (1 + w[zero_idx] * (np.exp(mu[zero_idx]) - 1))

        #d2l/dp2
        for i in range(self.k_exog):
            for j in range(i, -1, -1):
                hess_arr[i + self.k_inflate, j + self.k_inflate] = ((
                    self.exog[zero_idx, i] * self.exog[zero_idx, j] *
                    mu[zero_idx] * (w[zero_idx] - 1) * (1 / coeff -
                    w[zero_idx] * mu[zero_idx] * np.exp(mu[zero_idx]) /
                    coeff**2)).sum() - (mu[nonzero_idx] * self.exog[nonzero_idx, i] *
                    self.exog[nonzero_idx, j]).sum())

        #d2l/dw2
        for i in range(self.k_inflate):
            for j in range(i, -1, -1):
                hess_arr[i, j] = ((
                    self.exog_infl[zero_idx, i] * self.exog_infl[zero_idx, j] *
                    w[zero_idx] * (w[zero_idx] - 1) * (np.exp(mu[zero_idx]) - 1) *
                    (w[zero_idx] * ((np.exp(mu[zero_idx]) - 1) * w[zero_idx] + 2) -
                    1) / coeff**2).sum() +
                    (self.exog_infl[nonzero_idx, i] *
                     self.exog_infl[nonzero_idx, j] * w[nonzero_idx] *
                     (w[nonzero_idx] - 1)).sum())

        #d2l/dpdw
        for i in range(self.k_inflate):
            for j in range(self.k_exog):
                hess_arr[i, j + self.k_inflate] = -((
                    self.exog[zero_idx, j] * self.exog_infl[zero_idx, i] *
                    mu[zero_idx] * np.exp(mu[zero_idx]) * w[zero_idx] *
                    (w[zero_idx] - 1) / coeff**2).sum())

        tri_idx = np.triu_indices(dim, k=1)
        hess_arr[tri_idx] = hess_arr.T[tri_idx]

        return hess_arr

    def predict(self, params, exog=None, exog_infl=None, exposure=None,
                offset=None, which='mean'):
        """
        Predict response variable of a count model given exogenous variables.

        Notes
        -----
        If exposure is specified, then it will be logged by the method.
        The user does not need to log it first.
        """
        if exog is None:
            exog = self.exog
            offset = getattr(self, 'offset', 0)
            exposure = getattr(self, 'exposure', 0)

        if exog_infl is None:
            exog_infl = self.exog_infl

        if exposure is None:
            exposure = 0
        elif exposure != 0:
            exposure = np.log(exposure)

        if offset is None:
            offset = 0

        params_infl = params[:self.self.k_inflate]
        params_main = params[self.self.k_inflate:]

        lin_pred = np.dot(exog, params_main) + exposure + offset
        prob_poisson = 1 / (1 + np.exp(np.dot(exog_infl, params_infl)))
        prob_zero = (1 - prob_poisson) + prob_poisson * np.exp(-np.exp(lin_pred))

        if which == 'mean':
            return prob_poisson * np.exp(lin_pred)
        elif which == 'poisson-mean':
            return np.exp(lin_pred)
        elif which == 'linear':
            return lin_pred
        elif which == 'mean-nonzero':
            return prob_poisson * np.exp(lin_pred) / (1 - prob_zero)
        elif which == 'prob-zero':
            return  prob_zero
        elif which == 'prob':
            counts = np.atleast_2d(np.arange(0, np.max(self.endog)+1))
            w = self.model_infl.predict(params_infl)[:, None]
            w[w == 1.] = np.nextafter(1, 0)
            mu = self.model_main.predict(params_main)[:, None]
            return zipoisson.pmf(counts, mu, w)
        else:
            raise ValueError('keyword `which` not recognized')

class GenericZeroInflatedResults(CountResults):
    __doc__ = _discrete_results_docs % {
        "one_line_description" : "A results class for Generic Zero Inflated",
                    "extra_attr" : ""}

class ZeroInflatedPoissonResults(GenericZeroInflatedResults):
    __doc__ = _discrete_results_docs % {
        "one_line_description" : "A results class for Zero Inflated Poisson",
                    "extra_attr" : ""}

class L1GenericZeroInflatedResults(L1CountResults, GenericZeroInflatedResults):
    pass

class L1ZeroInflatedPoissonResults(L1CountResults, ZeroInflatedPoissonResults):
    pass

class GenericZeroInflatedResultsWrapper(lm.RegressionResultsWrapper):
    pass
wrap.populate_wrapper(GenericZeroInflatedResultsWrapper,
                      GenericZeroInflatedResults)

class ZeroInflatedPoissonResultsWrapper(lm.RegressionResultsWrapper):
    pass
wrap.populate_wrapper(ZeroInflatedPoissonResultsWrapper,
                      ZeroInflatedPoissonResults)

class L1GenericZeroInflatedResultsWrapper(lm.RegressionResultsWrapper):
    pass
wrap.populate_wrapper(L1GenericZeroInflatedResultsWrapper,
                      L1GenericZeroInflatedResults)

class L1ZeroInflatedPoissonResultsWrapper(lm.RegressionResultsWrapper):
    pass
wrap.populate_wrapper(L1ZeroInflatedPoissonResultsWrapper,
                      L1ZeroInflatedPoissonResults)


if __name__=="__main__":
    import numpy as np
    import statsmodels.api as sm

    data = sm.datasets.randhie.load()
    endog = data.endog
    exog = sm.add_constant(data.exog[:,1:4], prepend=False)
    exog_infl = sm.add_constant(data.exog[:,0], prepend=False)
    res1 = PoissonZeroInflated(data.endog, exog, exog_infl=exog_infl).fit(maxiter=500)

    print(res1.llf)