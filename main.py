from fastapi import FastAPI, Header
from pydantic import BaseModel
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    verify_token
)
from app.database import engine, SessionLocal
from app.models import Base, User, Holding

app = FastAPI()
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

class UserSignup(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class HoldingCreate(BaseModel):
    user_email: str
    ticker: str
    shares: int
    avg_price: float
    current_price: float

class PortfolioHolding(BaseModel):
    ticker: str
    shares: float
    avg_price: float
    current_price: float
    position_value: float
    weight: float
    profit_loss: float

class Portfolio(BaseModel):
    holdings: list[PortfolioHolding]
    total_value: float
    total_profit_loss: float
    portfolio_return_pct: float
    concentration_risk: str
    largest_holding: str
    holdings_count: int
    diversification_score: int
    overall_risk_score: int

@app.get("/")
def root():
    return {"message": "FinSight AI v2 is running"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/signup")
def signup(user: UserSignup):
    db = get_db()

    existing_user = db.query(User).filter(
        User.email == user.email
    ).first()

    if existing_user:
        return {
            "message": "user already exists",
            "email": user.email
        }

    hashed_password = hash_password(user.password)

    new_user = User(
        email=user.email,
        hashed_password=hashed_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "user created",
        "email": new_user.email,
        "id": new_user.id
    }

@app.post("/login")
def login(user: UserLogin):
    db = get_db()

    stored_user = db.query(User).filter(
        User.email == user.email
    ).first()

    if not stored_user:
        return {"message": "user not found"}

    if not verify_password(
        user.password,
        stored_user.hashed_password
    ):
        return {"message": "invalid password"}

    return {
        "message": "login successful",
        "email": stored_user.email,
        "access_token": create_access_token(stored_user.email),
        "token_type": "bearer"
    }

@app.get("/me")
def get_me(token: str):
    payload = verify_token(token)

    return {
        "email": payload["sub"]
    }

@app.get("/portfolio")
def get_portfolio(user_email: str):
    db = get_db()

    db_holdings = db.query(Holding).filter(
    Holding.user_email == user_email
    ).all()

    holdings = [
    PortfolioHolding(
        ticker=db_holding.ticker,
        shares=db_holding.shares,
        avg_price=db_holding.avg_price,
        current_price=db_holding.current_price,
        position_value=db_holding.shares * db_holding.current_price,
        weight=0,
        profit_loss=(db_holding.current_price - db_holding.avg_price) * db_holding.shares
    )
    for db_holding in db_holdings
    ]

    total_value = sum(
        holding.position_value
        for holding in holdings
    )

    total_profit_loss = sum(
        holding.profit_loss
        for holding in holdings
    )

    total_cost_basis = sum(
        holding.shares *holding.avg_price
        for holding in holdings
    )

    portfolio_return_pct = (
        total_profit_loss / total_cost_basis
    ) * 100

    for holding in holdings:
        holding.weight = (
            holding.position_value / total_value
        ) * 100
    
    largest_weight = max(
        holding.weight
        for holding in holdings
    )

    if largest_weight > 50:
        concentration_risk = "High"
    elif largest_weight > 30:
        concentration_risk = "Medium"
    else:
        concentration_risk = "Low"

    largest_holding = max(
    holdings,
    key=lambda holding: holding.weight
    ).ticker

    holdings_count = len(holdings)

    diversification_score = min(100, holdings_count * 20)
    
    overall_risk_score = 100 - diversification_score

    if concentration_risk == "High":
        overall_risk_score += 20
    elif concentration_risk == "Medium":
        overall_risk_score += 10

    overall_risk_score = min(100, overall_risk_score)

    portfolio = Portfolio(
        holdings=holdings,
        total_value=total_value,
        total_profit_loss=total_profit_loss,
        portfolio_return_pct=portfolio_return_pct,
        concentration_risk=concentration_risk, 
        largest_holding=largest_holding, 
        holdings_count=holdings_count, 
        diversification_score=diversification_score,
        overall_risk_score=overall_risk_score
    )

    return portfolio


@app.post("/holdings")
def create_holding(holding: HoldingCreate):
    db = get_db()

    existing_user = db.query(User).filter(
    User.email == holding.user_email
    ).first()

    existing_holding = db.query(Holding).filter(
    Holding.user_email == holding.user_email,
    Holding.ticker == holding.ticker
    ).first()

    if existing_holding:
        total_cost = (
            existing_holding.shares * existing_holding.avg_price
        ) + (
            holding.shares * holding.avg_price
        )

        total_shares = existing_holding.shares + holding.shares

        existing_holding.shares = total_shares
        existing_holding.avg_price = total_cost / total_shares
        existing_holding.current_price = holding.current_price

        db.commit()
        db.refresh(existing_holding)

        return {
            "message": "holding updated",
            "ticker": existing_holding.ticker,
            "shares": existing_holding.shares,
            "avg_price": existing_holding.avg_price
        }

    if not existing_user:
        return {
            "message": "user not found",
            "email": holding.user_email
        }

    new_holding = Holding(
        user_email=holding.user_email,
        ticker=holding.ticker,
        shares=holding.shares,
        avg_price=holding.avg_price,
        current_price=holding.current_price
    )

    db.add(new_holding)
    db.commit()
    db.refresh(new_holding)

    return {
        "message": "holding created",
        "id": new_holding.id,
        "ticker": new_holding.ticker
    }