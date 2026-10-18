import asyncio
import json
from pathlib import Path

from app.constants.policy_files import FILE_ENCODING, PAYERS_FILE, POLICY_FILE_GLOB
from app.interfaces.repository.policy_repository import IPolicyRepository
from app.schemas.payer import Payer
from app.schemas.policy_clause import PolicyClause
from app.schemas.policy_document import PolicyDocument


class FilePolicyRepository(IPolicyRepository):
    """Policies from versioned files: `payers.json` plus one folder of policies per payer.

    The files are read once, on first use, and held for the life of the process. They
    change only with a deployment, so every process holds the same copy.
    """

    def __init__(self, policies_dir: Path) -> None:
        self._policies_dir = policies_dir
        self._payers: dict[str, Payer] | None = None
        self._clauses: dict[str, PolicyClause] = {}

    async def get_payer(self, payer_id: str) -> Payer | None:
        return (await self._loaded_payers()).get(payer_id)

    async def list_clauses(self, payer_id: str) -> tuple[PolicyClause, ...]:
        await self._loaded_payers()
        return tuple(clause for clause in self._clauses.values() if clause.payer_id == payer_id)

    async def get_clause(self, clause_id: str) -> PolicyClause | None:
        await self._loaded_payers()
        return self._clauses.get(clause_id)

    async def _loaded_payers(self) -> dict[str, Payer]:
        if self._payers is None:
            payers, self._clauses = await asyncio.to_thread(self._read)
            self._payers = payers
            return payers
        return self._payers

    def _read(self) -> tuple[dict[str, Payer], dict[str, PolicyClause]]:
        raw_payers = json.loads(
            (self._policies_dir / PAYERS_FILE).read_text(encoding=FILE_ENCODING)
        )
        payers = {payer.payer_id: payer for payer in map(Payer.model_validate, raw_payers)}

        clauses: dict[str, PolicyClause] = {}
        for path in sorted(self._policies_dir.glob(POLICY_FILE_GLOB)):
            document = PolicyDocument.model_validate_json(path.read_text(encoding=FILE_ENCODING))
            if document.payer_id not in payers:
                raise ValueError(f"{path.name} belongs to unknown payer {document.payer_id}")
            for clause in document.to_clauses():
                if clause.clause_id in clauses:
                    raise ValueError(f"clause {clause.clause_id} is defined twice")
                clauses[clause.clause_id] = clause
        return payers, clauses
