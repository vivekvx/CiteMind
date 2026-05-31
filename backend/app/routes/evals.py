from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.rate_limit import enforce_rate_limit
from backend.app.db.database import get_db
from backend.app.models.eval_result import EvalResult
from backend.app.schemas.eval import EvalRunRequest, EvalRunResponse
from backend.app.services.evaluator import evaluate


router = APIRouter(prefix="/evals", tags=["evals"], dependencies=[Depends(enforce_rate_limit)])


@router.post("/run", response_model=EvalRunResponse)
def run_eval(
    request: EvalRunRequest,
    db: Session = Depends(get_db),
) -> EvalRunResponse:
    scores = evaluate(request)
    result = EvalResult(
        query=request.query,
        answer=request.answer,
        **scores,
    )
    db.add(result)
    db.commit()
    db.refresh(result)

    return EvalRunResponse(id=result.id, **scores)
