from limix._cache import cache
from limix.stats import lrt_pvalues

from ._aligned import Aligned
from ._draw import draw_alt_hyp_table, draw_lrt_table, draw_model, draw_title


class STScanResult:
    def __init__(self, tests, trait, covariates, candidates, h0, envs0, envs1):
        self._tests = tests
        self._trait = trait
        self._covariates = covariates
        self._candidates = candidates
        self._envs0 = envs0
        self._envs1 = envs1
        self._h0 = h0

    @property
    def stats(self):
        """
        Statistics.
        """
        return self._dataframes["stats"].set_index("test")

    @property
    def effsizes(self):
        """
        Effect sizes.
        """
        return self._dataframes["effsizes"]

    @property
    def h0(self):
        """
        Hypothesis zero.
        """
        return self._h0

    @property
    def _h0_dataframe(self):
        from pandas import DataFrame

        covariates = list(self._covariates)

        h0 = []
        for j, c in enumerate(covariates):
            eff = self._h0["effsizes"][j]
            eff_se = self._h0["effsizes_se"][j]
            h0.append([self._trait, "covariate", c, eff, eff_se])

        columns = ["trait", "effect_type", "effect_name", "effsize", "effsize_se"]
        return DataFrame(h0, columns=columns)

    @property
    def _h1_dataframe(self):
        from pandas import DataFrame

        covariates = list(self._covariates)
        envs0 = list(self._envs0)

        h1 = []
        for i, test in enumerate(self._tests):
            candidates = list(self._candidates[test["idx"]])

            effsizes = test["h1"]["covariate_effsizes"]
            effsizes_se = test["h1"]["covariate_effsizes_se"]
            for l, c in enumerate(covariates):
                eff = effsizes[l]
                eff_se = effsizes_se[l]
                v = [i, self._trait, "covariate", str(c), None, eff, eff_se]
                h1.append(v)

            effsizes = test["h1"]["candidate_effsizes"]
            effsizes_se = test["h1"]["candidate_effsizes_se"]
            for j, e in enumerate(envs0):
                for l, c in enumerate(candidates):
                    env_name = "env0_" + str(e)
                    eff = effsizes[l, j]
                    eff_se = effsizes_se[l, j]
                    v = [i, self._trait, "candidate", str(c), env_name, eff, eff_se]
                    h1.append(v)

        columns = [
            "test",
            "trait",
            "effect_type",
            "effect_name",
            "env",
            "effsize",
            "effsize_se",
        ]
        return DataFrame(h1, columns=columns)

    @property
    def _h2_dataframe(self):
        from pandas import DataFrame

        envs0 = list(self._envs0)
        envs1 = list(self._envs1)
        covariates = list(self._covariates)

        h2 = []
        for i, test in enumerate(self._tests):
            candidates = list(self._candidates[test["idx"]])

            effsizes = test["h2"]["covariate_effsizes"]
            effsizes_se = test["h2"]["covariate_effsizes_se"]
            for l, c in enumerate(covariates):
                eff = effsizes[l]
                eff_se = effsizes_se[l]
                v = [i, self._trait, "covariate", str(c), None, eff, eff_se]
                h2.append(v)

            effsizes = test["h2"]["candidate_effsizes"]
            effsizes_se = test["h2"]["candidate_effsizes_se"]
            off = 0
            for j, e in enumerate(envs0):
                for l, c in enumerate(candidates):
                    env_name = "env0_" + str(e)
                    eff = effsizes[l, off + j]
                    eff_se = effsizes_se[l, off + j]
                    v = [i, self._trait, "candidate", str(c), env_name, eff, eff_se]
                    h2.append(v)

            off = len(envs0)
            for j, e in enumerate(envs1):
                for l, c in enumerate(candidates):
                    env_name = "env1_" + str(e)
                    eff = effsizes[l, off + j]
                    eff_se = effsizes_se[l, off + j]
                    v = [i, self._trait, "candidate", str(c), env_name, eff, eff_se]
                    h2.append(v)

        columns = [
            "test",
            "trait",
            "effect_type",
            "effect_name",
            "env",
            "effsize",
            "effsize_se",
        ]
        return DataFrame(h2, columns=columns)

    @property
    def _stats_dataframe(self):
        from pandas import DataFrame

        stats = []
        for i, test in enumerate(self._tests):
            dof10 = test["h1"]["candidate_effsizes"].size
            dof20 = test["h2"]["candidate_effsizes"].size
            dof21 = dof20 - dof10
            stats.append(
                [
                    i,
                    self._h0.lml,
                    test["h1"]["lml"],
                    test["h2"]["lml"],
                    dof10,
                    dof20,
                    dof21,
                    test["h1"]["scale"],
                    test["h2"]["scale"],
                ]
            )

        columns = [
            "test",
            "lml0",
            "lml1",
            "lml2",
            "dof10",
            "dof20",
            "dof21",
            "scale1",
            "scale2",
        ]
        stats = DataFrame(stats, columns=columns)

        stats["pv10"] = lrt_pvalues(stats["lml0"], stats["lml1"], stats["dof10"])
        stats["pv20"] = lrt_pvalues(stats["lml0"], stats["lml2"], stats["dof20"])
        stats["pv21"] = lrt_pvalues(stats["lml1"], stats["lml2"], stats["dof21"])

        return stats

    @property
    @cache
    def _dataframes(self):
        h1 = self._h1_dataframe
        h2 = self._h2_dataframe
        stats = self._stats_dataframe

        return {"stats": stats, "effsizes": {"h1": h1, "h2": h2}}

    def _covariance_expr(self):
        from numpy import isnan

        v0 = self.h0.variances["fore_covariance"].item()
        v1 = self.h0.variances["back_covariance"].item()

        if isnan(v0):
            covariance = f"{v1:.3f}⋅𝙸"
        else:
            covariance = f"{v0:.3f}⋅𝙺 + {v1:.3f}⋅𝙸"

        return covariance

    def __repr__(self):
        from numpy import asarray

        trait = self._h0.trait
        lik = self._h0.likelihood
        covariates = self._covariates
        lml = self._h0.lml
        effsizes = asarray(self.h0.effsizes["effsize"], float).ravel()
        effsizes_se = asarray(self.h0.effsizes["effsize_se"], float).ravel()
        stats = self.stats

        df = self.h0.variances
        df = df[df["trait0"] == df["trait1"]]

        covariance = self._covariance_expr()

        msg = draw_title("Hypothesis 0")
        msg += draw_model(lik, "𝙼𝜶", covariance) + "\n"
        msg += _draw_hyp0_summary(trait, covariates, effsizes, effsizes_se, lml)

        msg += draw_title(f"Hypothesis 2")
        msg += draw_model(lik, "𝙼𝜶 + G𝛃", f"s({covariance})")
        msg += draw_alt_hyp_table(2, self.stats, self.effsizes)

        msg += draw_title("Likelihood-ratio test p-values")
        msg += draw_lrt_table(["𝓗₀ vs 𝓗₂"], [f"pv20"], stats)
        return msg


def _draw_hyp0_summary(covariates, effsizes, effsizes_se, lml):
    aligned = Aligned()
    aligned.add_item("M", covariates)
    aligned.add_item("𝜶", effsizes)
    aligned.add_item("se(𝜶)", effsizes_se)
    aligned.add_item("lml", lml)
    return aligned.draw() + "\n"
