from dependency_injector import containers, providers

from app.utilities.async_task_runner import AsyncTaskRunner
from app.utilities.bm25_scorer import Bm25Scorer
from app.utilities.case_renderer import CaseRenderer
from app.utilities.iso_date_shifter import IsoDateShifter
from app.utilities.quote_matcher import QuoteMatcher
from app.utilities.response_builder import ResponseBuilder
from app.utilities.system_clock import SystemClock
from app.utilities.uuid_generator import UuidGenerator
from app.utilities.word_tokenizer import WordTokenizer


class UtilityContainer(containers.DeclarativeContainer):
    clock = providers.Singleton(SystemClock)
    response_builder = providers.Singleton(ResponseBuilder, clock=clock)
    tokenizer = providers.Singleton(WordTokenizer)
    text_scorer = providers.Singleton(Bm25Scorer)
    case_renderer = providers.Singleton(CaseRenderer)
    id_generator = providers.Singleton(UuidGenerator)
    date_shifter = providers.Singleton(IsoDateShifter)
    quote_matcher = providers.Singleton(QuoteMatcher)
    # One per process: it holds the background runs that are still going.
    task_runner = providers.Singleton(AsyncTaskRunner)
