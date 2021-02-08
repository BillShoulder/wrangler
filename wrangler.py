"""
Suggest normalized terms for a set of terms containing minor errors.
"""

#######################################################################################################################
#
#   Import
#
#######################################################################################################################

from abc import ABC, abstractproperty
from collections import Counter
from functools import cached_property

from fuzzywuzzy.process import extractBests


#######################################################################################################################
#
#   BaseWrangler
#
#######################################################################################################################

class BaseWrangler(ABC):
    """ Suggest normalized terms for a set of terms containing minor errors. """
    
    def __init__(self, terms: list[str]):
        self._terms_ = terms

    @property
    def _counter_(self):
        return Counter(self._terms_)

    @property
    def _unique_terms_(self):
        return set(self._terms_)

    @abstractproperty
    def substitutions(self):
        raise NotImplementedError("This abstract property must be implemented in any derived classes.")

    @cached_property
    def wrangled_terms(self):
        wrangled_terms = []
        for term in self._terms_:
            if (updated_term := self.substitutions.get(term)) is not None:
                wrangled_terms.append(updated_term)
            else:
                wrangled_terms.append(term)
        return wrangled_terms

    def wrangle(self, term):
        assert term in self._terms_, f"Cannot wrangle a term outside the original input terms: {term}"
        return term if (sub := self.substitutions.get(term)) is None else sub


#######################################################################################################################
#
#   CapsWrangler
#
#######################################################################################################################

class CapsWrangler(BaseWrangler):
    """ Suggest normalized capitalization over a series of terms. """

    def _get_preferred_capitalization_(self, term):
        lower_term = term.lower()
        best_term = None
        best_count = 0
        for alt_term, count in self._counter_.items():
            if lower_term == alt_term.lower() and count > best_count:
                best_term = alt_term
                best_count = count
        return best_term

    @cached_property
    def substitutions(self):
        substitutions = {}
        for term in self._unique_terms_:
            if (preferred_cap := self._get_preferred_capitalization_(term)) != term:
                substitutions[term] = preferred_cap
        return substitutions


#######################################################################################################################
#
#   TextWrangler
#
#######################################################################################################################

class TextWrangler(BaseWrangler):
    """ Suggest normalized text over a series of terms. """

    def __init__(self, terms: list[str], threshold=94):
        super().__init__(terms)
        self._threshold_ = threshold

    @cached_property
    def substitutions(self):
        substitutions = {}
        for term in self._unique_terms_:
            closest_terms = extractBests(term, self._unique_terms_, limit=2)
            if len(closest_terms) > 1:
                closest_term = closest_terms[-1]
                if closest_term[1] > self._threshold_:
                    if self._counter_[closest_term[0]] >= self._counter_[term]:
                        substitutions[term] = closest_term[0]
        return substitutions


#######################################################################################################################
#
#   Wrangler
#
#######################################################################################################################

class Wrangler(BaseWrangler):
    """ Calculate substitutions by successive application of Caps and Text substitutions. """
    @cached_property
    def substitutions(self):
        caps_wrangler = CapsWrangler(self._terms_)
        text_wrangler = TextWrangler(caps_wrangler.wrangled_terms)
        substitutions = caps_wrangler.substitutions
        for term, caps_sub in substitutions.items():
            if (text_sub := text_wrangler.substitutions.get(caps_sub)) is not None:
                substitutions[term] = text_sub
        for term, text_sub in text_wrangler.substitutions.items():
            substitutions[term] = text_sub
        return substitutions
