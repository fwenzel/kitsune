from functools import partial

from django.conf import settings
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.utils.datastructures import SortedDict
from django.views.decorators.http import require_GET

import jingo
from mobility.decorators import mobile_template
from tower import ugettext_lazy as _lazy, ugettext as _

from dashboards.readouts import (overview_rows, READOUTS, L10N_READOUTS,
                                 CONTRIBUTOR_READOUTS)
from sumo_locales import LOCALES
from sumo.parser import get_object_fallback
from sumo.urlresolvers import reverse
from sumo.utils import smart_int
from wiki.events import (ApproveRevisionInLocaleEvent,
                         ReviewableRevisionInLocaleEvent)
from wiki.models import Document
from wiki.views import SHOWFOR_DATA


HOME_DOCS = {'quick': 'Home page - Quick', 'explore': 'Home page - Explore'}
MOBILE_DOCS = {'quick': 'Mobile home - Quick',
               'explore': 'Mobile home - Explore'}
HOME_DOCS_FOR_MOBILE = {'common':
                        'Desktop home for mobile - Common Questions'}
MOBILE_DOCS_FOR_MOBILE = {'common':
                          'Mobile home for mobile - Common Questions'}


@mobile_template('dashboards/{mobile/}home.html')
def home(request, template=None):
    data = {}
    docs = HOME_DOCS_FOR_MOBILE if request.MOBILE else HOME_DOCS
    for side, title in docs.iteritems():
        message = _lazy(u'The template "%s" does not exist.') % title
        data[side] = get_object_fallback(
            Document, title, request.locale, message)

    data.update(SHOWFOR_DATA)
    return jingo.render(request, template, data)


@mobile_template('dashboards/{mobile/}mobile.html')
def mobile(request, template=None):
    data = {}
    docs = MOBILE_DOCS_FOR_MOBILE if request.MOBILE else MOBILE_DOCS
    for side, title in docs.iteritems():
        message = _lazy(u'The template "%s" does not exist.') % title
        data[side] = get_object_fallback(
            Document, title, request.locale, message)

    data.update(SHOWFOR_DATA)
    return jingo.render(request, template, data)


def _kb_readout(request, readout_slug, readouts, locale=None, mode=None):
    """Instantiate and return the readout with the given slug.

    Raise Http404 if there is no such readout.

    """
    if readout_slug not in readouts:
        raise Http404
    return readouts[readout_slug](request, locale=locale, mode=mode)


def _kb_detail(request, readout_slug, readouts, main_view_name,
               main_dash_title, locale=None):
    """Show all the rows for the given KB article statistics table."""
    return jingo.render(request, 'dashboards/kb_detail.html',
        {'readout': _kb_readout(request, readout_slug, readouts, locale),
         'locale': locale,
         'main_dash_view': main_view_name,
         'main_dash_title': main_dash_title})


@require_GET
def contributors_detail(request, readout_slug):
    """Show all the rows for the given contributor dashboard table."""
    return _kb_detail(request, readout_slug, CONTRIBUTOR_READOUTS,
                      'dashboards.contributors', _('Contributor Dashboard'),
                      locale=settings.WIKI_DEFAULT_LANGUAGE)


@require_GET
def localization_detail(request, readout_slug):
    """Show all the rows for the given localizer dashboard table."""
    return _kb_detail(request, readout_slug, L10N_READOUTS,
                      'dashboards.localization', _('Localization Dashboard'))


def _kb_main(request, readouts, template, locale=None, extra_data=None):
    """Render a KB statistics overview page.

    Use the given template, pass the template the given readouts, limit the
    considered data to the given locale, and pass along anything in the
    `extra_data` dict to the template in addition to the standard data.

    """
    data = {'readouts': SortedDict((slug, class_(request, locale=locale))
                         for slug, class_ in readouts.iteritems()),
            'default_locale': settings.WIKI_DEFAULT_LANGUAGE,
            'default_locale_name':
                LOCALES[settings.WIKI_DEFAULT_LANGUAGE].native,
            'current_locale_name': LOCALES[request.locale].native,
            'is_watching_approved': ApproveRevisionInLocaleEvent.is_notifying(
                request.user, locale=request.locale),
            'is_watching_locale': ReviewableRevisionInLocaleEvent.is_notifying(
                request.user, locale=request.locale),
            'is_watching_approved_default':
                ApproveRevisionInLocaleEvent.is_notifying(
                    request.user, locale=settings.WIKI_DEFAULT_LANGUAGE)}
    if extra_data:
        data.update(extra_data)
    return jingo.render(request, 'dashboards/' + template, data)


@require_GET
def localization(request):
    """Render aggregate data about articles in a non-default locale."""
    if request.locale == settings.WIKI_DEFAULT_LANGUAGE:
        return HttpResponseRedirect(reverse('dashboards.contributors'))
    data = {'overview_rows': partial(overview_rows, request.locale)}
    return _kb_main(request, L10N_READOUTS, 'localization.html',
                    extra_data=data)


@require_GET
def contributors(request):
    """Render aggregate data about the articles in the default locale."""
    return _kb_main(request, CONTRIBUTOR_READOUTS, 'contributors.html',
                    locale=settings.WIKI_DEFAULT_LANGUAGE)


@require_GET
def wiki_rows(request, readout_slug):
    """Return the table contents HTML for the given readout and mode."""
    readout = _kb_readout(request, readout_slug, READOUTS,
                          locale=request.GET.get('locale'),
                          mode=smart_int(request.GET.get('mode'), None))
    max_rows = smart_int(request.GET.get('max'), fallback=None)
    return HttpResponse(readout.render(max_rows=max_rows))
