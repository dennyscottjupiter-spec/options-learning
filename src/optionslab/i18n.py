"""
Two string catalogs, English and Portuguese (Brazil). report.py picks one by
`lang` ('en' | 'pt-BR') and hands the whole dict to the Jinja template, so the
template never branches on language itself — only on `mode` (Learn/Pro).
"""
from __future__ import annotations

STRATEGY_NAMES = {
    "en": {
        "long_call": "Long Call (LEAPS)",
        "cash_secured_put": "Cash-Secured Put",
        "covered_call": "Covered Call",
        "protective_put": "Protective Put",
    },
    "pt-BR": {
        "long_call": "Compra de Call (LEAPS)",
        "cash_secured_put": "Venda de Put Coberta por Caixa",
        "covered_call": "Venda de Call Coberta",
        "protective_put": "Compra de Put Protetora",
    },
}

STRATEGY_BLURBS = {
    "en": {
        "long_call": "Buy the right to purchase the stock at today's price, months or "
        "years from now, paying only a fraction of the share price in premium. This is "
        "the 'acquire it cheaper later' play: if the stock rises, you profit far more "
        "than owning shares outright would have cost you; if it doesn't, the most you "
        "lose is the premium.",
        "cash_secured_put": "Sell someone else the right to make you buy the stock at a "
        "price you chose, and get paid a premium today for taking on that obligation. "
        "Worst case, you end up owning a stock you already wanted, at a discount to "
        "today's price.",
        "covered_call": "Sell someone else the right to buy your shares at a price above "
        "today's, and collect a premium for it. Turns stock that would otherwise just "
        "sit there into income — at the cost of capping your upside if the stock rallies "
        "hard.",
        "protective_put": "Buy insurance on shares you already own: a guaranteed minimum "
        "sale price for the life of the contract, in exchange for a premium. Upside stays "
        "fully open; downside is floored.",
    },
    "pt-BR": {
        "long_call": "Compre o direito de adquirir a ação pelo preço de hoje, daqui a "
        "meses ou anos, pagando apenas uma fração do preço da ação como prêmio. Esta é a "
        "estratégia de 'adquirir mais barato no futuro': se a ação subir, o lucro supera "
        "em muito o custo de possuir as ações diretamente; se não subir, a perda máxima é "
        "o prêmio pago.",
        "cash_secured_put": "Venda a alguém o direito de te obrigar a comprar a ação a um "
        "preço que você escolheu, e receba um prêmio hoje por assumir essa obrigação. No "
        "pior caso, você acaba comprando uma ação que já queria, com desconto sobre o "
        "preço de hoje.",
        "covered_call": "Venda a alguém o direito de comprar suas ações a um preço acima "
        "do atual, e receba um prêmio por isso. Transforma ações paradas em renda — ao "
        "custo de limitar seu ganho caso a ação suba forte.",
        "protective_put": "Compre um seguro sobre ações que você já possui: um preço "
        "mínimo garantido de venda durante a vigência do contrato, em troca de um prêmio. "
        "O potencial de alta permanece aberto; a queda fica limitada.",
    },
}

CATALOG = {
    "en": {
        "report_title": "Options Analysis",
        "generated_on": "Generated",
        "mode_learn": "Learn",
        "mode_pro": "Pro",
        "lang_toggle": "Português",
        "spot_price": "Spot price",
        "sector": "Sector",
        "market_cap": "Market cap",
        "next_earnings": "Next earnings",
        "candidates_evaluated": "Candidates evaluated",
        "why_best": "Why this contract",
        "why_best_template": "#1 ({best_symbol}, strike {best_strike:g}) scores "
        "{best_score:.3f} annualized risk-adjusted return per dollar at risk, vs #2 "
        "({runner_up_symbol}, strike {runner_up_strike:g}) at {runner_up_score:.3f} — a "
        "{margin:.3f} edge.",
        "contract_section": "The contract",
        "strike": "Strike",
        "moneyness_itm": "ITM",
        "moneyness_atm": "ATM",
        "moneyness_otm": "OTM",
        "expiration": "Expiration",
        "dte": "Days to expiration",
        "premium": "Premium",
        "intrinsic_value": "Intrinsic",
        "extrinsic_value": "Extrinsic",
        "breakeven": "Breakeven",
        "max_profit": "Max profit",
        "max_loss": "Max loss",
        "net_of_commissions": "Net of commissions",
        "assignment_tax_note": "Assignment on this covered call sells your 100 shares at the "
        "strike — a stock sale, which is a taxable event.",
        "capital_required": "Capital required",
        "unlimited": "Unlimited",
        "greeks_section": "Greeks & implied volatility",
        "delta": "Delta",
        "gamma": "Gamma",
        "theta": "Theta (per day)",
        "vega": "Vega (per 1% vol)",
        "rho": "Rho (per 1% rate)",
        "implied_volatility": "Implied volatility",
        "greeks_source_alpaca": "from Alpaca",
        "greeks_source_local": "calculated locally",
        "probability_section": "Probability of profit",
        "pop_closed_form": "Closed-form (lognormal)",
        "pop_monte_carlo": "Monte Carlo (100,000 paths)",
        "pop_disagreement": "These two estimates disagree by more than expected — a sign "
        "the lognormal assumption may be straining for this contract.",
        "probability_of_touch": "Probability of touching breakeven before expiration",
        "avg_win": "Average win (simulated)",
        "avg_loss": "Average loss (simulated)",
        "score": "Risk-adjusted score (annualized)",
        "technical_section": "Technical snapshot",
        "sma20": "SMA 20",
        "sma50": "SMA 50",
        "sma200": "SMA 200",
        "rsi14": "RSI (14)",
        "hv30": "Historical volatility (30d)",
        "hv90": "Historical volatility (90d)",
        "percentile_suffix": "percentile of the past year",
        "range_52w": "52-week range",
        "directional_bias": "Directional bias",
        "bias_bullish": "Bullish (price above rising averages)",
        "bias_bearish": "Bearish (price below falling averages)",
        "bias_mixed": "Mixed / no clear trend",
        "bias_insufficient": "Not enough price history yet",
        "earnings_warning_title": "Earnings inside this window",
        "earnings_warning_body": "This contract's expiration is after the next earnings "
        "date. Earnings moves are unpredictable and implied volatility typically collapses "
        "the morning after the report (an effect called IV crush) — both the price and the "
        "probability estimates above are less reliable across an earnings date than they "
        "are for an ordinary stretch of trading.",
        "liquidity_warning_title": "Thin liquidity",
        "liquidity_warning_body": "This contract's quoted size or bid-ask spread misses "
        "this project's liquidity bar. You can still trade it, but expect to give up more "
        "to the spread getting in and out than a more liquid strike would cost you.",
        "affordability_warning_title": "Exceeds paper buying power",
        "affordability_warning_body": "The capital this trade requires is more than your "
        "paper account's current buying power.",
        "early_assignment_warning_title": "Early assignment risk",
        "early_assignment_warning_body_covered_call": "The option buyer can exercise this "
        "contract at any time before expiration, not just at expiry. This call is "
        "in-the-money with an ex-dividend date before expiration, so the shares are more "
        "likely to be called away early — the buyer captures the dividend, and your "
        "position closes sooner than the payoff diagram assumes.",
        "early_assignment_warning_body_cash_secured_put": "The option buyer can exercise "
        "this contract at any time before expiration, not just at expiry. This put is "
        "in-the-money with an ex-dividend date before expiration, so the shares are more "
        "likely to be put to you early, closing your position sooner than the payoff "
        "diagram assumes.",
        "expected_return_note": "Under the model's own risk-neutral assumptions, every "
        "option's expected profit is approximately zero minus trading costs — the "
        "probabilities above describe likely outcomes, not a positive edge. A profitable "
        "trade requires a directional view this model does not have.",
        "footer_disclaimer": "Educational tool only. Data from Alpaca's paper trading API "
        "and yfinance. Not investment advice — this is a practice environment for "
        "learning options mechanics, not a signal to trade real money.",
        "breakeven_vs_strike_note": "Notice breakeven isn't the strike — it's the strike "
        "adjusted for the premium paid or received. Probability of profit is measured "
        "against breakeven, since that's the price the position actually needs to clear.",
        "app_title": "Options Lab",
        "app_tagline": "Learn options mechanics on real contracts, before risking real money.",
        "home_analyze_title": "Analyze a ticker",
        "adjust_selection_title": "Adjust selection",
        "ticker_label": "Ticker",
        "ticker_placeholder": "e.g. AAPL",
        "strategy_label": "Strategy",
        "expiration_override_label": "Expiration override",
        "analyze_button": "Analyze",
        "update_button": "Update",
        "watchlist_title": "Watchlist",
        "watchlist_empty": "No tickers yet — add one above.",
        "watchlist_add_placeholder": "Add ticker",
        "add_to_watchlist_button": "Add to watchlist",
        "remove_button": "Remove",
        "data_unavailable": "Data unavailable",
        "back_to_dashboard": "← Dashboard",
        "download_pdf": "Download PDF",
        "view_report": "View report",
        "methodology_title": "Methodology — every number, verifiable",
        "methodology_intro": "Every figure above comes from this project's own math "
        "engine, computed locally, right now — no third-party black box. Full source "
        "tree:",
        "methodology_col_metric": "Metric",
        "methodology_col_formula": "Formula",
        "methodology_col_source": "Source (file :: function)",
        "static_demo_title": "Static demo — frozen sample data",
        "static_demo_body": "This page is a snapshot for portfolio purposes, not the live app. "
        "The real tool runs locally, pulling live prices and option chains from Alpaca's paper "
        "trading API, with a full watchlist dashboard and PDF export.",
        "static_index_intro": "Below is a real, frozen snapshot of the report page — payoff "
        "diagram, Greeks, probability of profit, and the full transparency methodology. Try dark "
        "mode above, then open the sample (it links out to a Portuguese version and a Pro-mode "
        "view too).",
        "static_index_cta": "Open the sample report",
    },
    "pt-BR": {
        "report_title": "Análise de Opções",
        "generated_on": "Gerado em",
        "mode_learn": "Aprender",
        "mode_pro": "Pro",
        "lang_toggle": "English",
        "spot_price": "Preço atual",
        "sector": "Setor",
        "market_cap": "Valor de mercado",
        "next_earnings": "Próximo resultado",
        "candidates_evaluated": "Contratos avaliados",
        "why_best": "Por que este contrato",
        "why_best_template": "#1 ({best_symbol}, strike {best_strike:g}) tem pontuação "
        "{best_score:.3f} de retorno ajustado ao risco anualizado por dólar em risco, "
        "contra #2 ({runner_up_symbol}, strike {runner_up_strike:g}) com {runner_up_score:.3f} "
        "— uma vantagem de {margin:.3f}.",
        "contract_section": "O contrato",
        "strike": "Strike",
        "moneyness_itm": "ITM",
        "moneyness_atm": "ATM",
        "moneyness_otm": "OTM",
        "expiration": "Vencimento",
        "dte": "Dias até o vencimento",
        "premium": "Prêmio",
        "intrinsic_value": "Intrínseco",
        "extrinsic_value": "Extrínseco",
        "breakeven": "Ponto de equilíbrio",
        "max_profit": "Lucro máximo",
        "max_loss": "Perda máxima",
        "net_of_commissions": "Líquido de comissões",
        "assignment_tax_note": "O exercício desta covered call vende suas 100 ações ao "
        "strike — uma venda de ações, o que é um evento tributável.",
        "capital_required": "Capital necessário",
        "unlimited": "Ilimitado",
        "greeks_section": "Gregas e volatilidade implícita",
        "delta": "Delta",
        "gamma": "Gama",
        "theta": "Theta (por dia)",
        "vega": "Vega (por 1% de vol.)",
        "rho": "Rho (por 1% de juros)",
        "implied_volatility": "Volatilidade implícita",
        "greeks_source_alpaca": "da Alpaca",
        "greeks_source_local": "calculado localmente",
        "probability_section": "Probabilidade de lucro",
        "pop_closed_form": "Fórmula fechada (lognormal)",
        "pop_monte_carlo": "Monte Carlo (100.000 simulações)",
        "pop_disagreement": "Essas duas estimativas divergem mais do que o esperado — um "
        "sinal de que a suposição lognormal pode não se sustentar bem para este contrato.",
        "probability_of_touch": "Probabilidade de tocar o ponto de equilíbrio antes do "
        "vencimento",
        "avg_win": "Ganho médio (simulado)",
        "avg_loss": "Perda média (simulada)",
        "score": "Pontuação ajustada ao risco (anualizada)",
        "technical_section": "Panorama técnico",
        "sma20": "Média Móvel 20",
        "sma50": "Média Móvel 50",
        "sma200": "Média Móvel 200",
        "rsi14": "IFR (14)",
        "hv30": "Volatilidade histórica (30d)",
        "hv90": "Volatilidade histórica (90d)",
        "percentile_suffix": "percentil do último ano",
        "range_52w": "Faixa de 52 semanas",
        "directional_bias": "Viés direcional",
        "bias_bullish": "Altista (preço acima de médias ascendentes)",
        "bias_bearish": "Baixista (preço abaixo de médias descendentes)",
        "bias_mixed": "Misto / sem tendência clara",
        "bias_insufficient": "Histórico de preços ainda insuficiente",
        "earnings_warning_title": "Resultado dentro desta janela",
        "earnings_warning_body": "O vencimento deste contrato é depois da próxima data de "
        "resultados. Movimentos de resultado são imprevisíveis e a volatilidade implícita "
        "costuma despencar na manhã seguinte ao anúncio (efeito chamado de 'IV crush') — "
        "tanto o preço quanto as probabilidades acima são menos confiáveis atravessando "
        "uma data de resultados do que em um período comum de negociação.",
        "liquidity_warning_title": "Liquidez baixa",
        "liquidity_warning_body": "O tamanho cotado ou o spread de compra/venda deste "
        "contrato não atinge o critério de liquidez deste projeto. Ainda é possível "
        "negociá-lo, mas espere perder mais no spread ao entrar e sair do que perderia em "
        "um strike mais líquido.",
        "affordability_warning_title": "Excede o poder de compra simulado",
        "affordability_warning_body": "O capital exigido por esta operação é maior que o "
        "poder de compra atual da sua conta simulada (paper).",
        "early_assignment_warning_title": "Risco de exercício antecipado",
        "early_assignment_warning_body_covered_call": "O comprador da opção pode exercer "
        "este contrato a qualquer momento antes do vencimento, não apenas no vencimento. "
        "Esta call está dentro do dinheiro com uma data ex-dividendo antes do vencimento, "
        "então as ações têm mais chance de ser exercidas antecipadamente — o comprador "
        "captura o dividendo, e sua posição se encerra antes do que o diagrama de payoff "
        "pressupõe.",
        "early_assignment_warning_body_cash_secured_put": "O comprador da opção pode "
        "exercer este contrato a qualquer momento antes do vencimento, não apenas no "
        "vencimento. Esta put está dentro do dinheiro com uma data ex-dividendo antes do "
        "vencimento, então as ações têm mais chance de ser exercidas contra você "
        "antecipadamente, encerrando sua posição antes do que o diagrama de payoff "
        "pressupõe.",
        "expected_return_note": "Sob as próprias premissas neutras a risco do modelo, o "
        "lucro esperado de qualquer opção é aproximadamente zero menos custos de "
        "negociação — as probabilidades acima descrevem resultados prováveis, não uma "
        "vantagem positiva. Uma operação lucrativa exige uma visão direcional que este "
        "modelo não possui.",
        "footer_disclaimer": "Ferramenta apenas educacional. Dados da API de paper "
        "trading da Alpaca e do yfinance. Não é recomendação de investimento — este é um "
        "ambiente de prática para aprender a mecânica de opções, não um sinal para operar "
        "com dinheiro real.",
        "breakeven_vs_strike_note": "Note que o ponto de equilíbrio não é o strike — é o "
        "strike ajustado pelo prêmio pago ou recebido. A probabilidade de lucro é medida "
        "em relação ao ponto de equilíbrio, pois esse é o preço que a posição realmente "
        "precisa superar.",
        "app_title": "Options Lab",
        "app_tagline": "Aprenda a mecânica de opções em contratos reais, antes de arriscar "
        "dinheiro de verdade.",
        "home_analyze_title": "Analisar um ticker",
        "adjust_selection_title": "Ajustar seleção",
        "ticker_label": "Ticker",
        "ticker_placeholder": "ex.: AAPL",
        "strategy_label": "Estratégia",
        "expiration_override_label": "Vencimento personalizado",
        "analyze_button": "Analisar",
        "update_button": "Atualizar",
        "watchlist_title": "Lista de acompanhamento",
        "watchlist_empty": "Nenhum ticker ainda — adicione um acima.",
        "watchlist_add_placeholder": "Adicionar ticker",
        "add_to_watchlist_button": "Adicionar à lista",
        "remove_button": "Remover",
        "data_unavailable": "Dados indisponíveis",
        "back_to_dashboard": "← Painel",
        "download_pdf": "Baixar PDF",
        "view_report": "Ver relatório",
        "methodology_title": "Metodologia — todo número, verificável",
        "methodology_intro": "Todo número acima vem do próprio motor matemático deste "
        "projeto, calculado localmente, agora — nenhuma caixa-preta de terceiros. "
        "Árvore de código-fonte completa:",
        "methodology_col_metric": "Métrica",
        "methodology_col_formula": "Fórmula",
        "methodology_col_source": "Origem (arquivo :: função)",
        "static_demo_title": "Demonstração estática — dados de amostra congelados",
        "static_demo_body": "Esta página é um retrato para fins de portfólio, não o aplicativo "
        "ao vivo. A ferramenta real roda localmente, buscando preços e cadeias de opções em tempo "
        "real na API de paper trading da Alpaca, com um painel completo de lista de "
        "acompanhamento e exportação em PDF.",
        "static_index_intro": "Abaixo está um retrato real e congelado da página de relatório — "
        "diagrama de payoff, gregas, probabilidade de lucro e a metodologia completa de "
        "transparência. Experimente o modo escuro acima, depois abra a amostra (ela também leva a "
        "uma versão em português e a uma visualização no modo Pro).",
        "static_index_cta": "Abrir relatório de amostra",
    },
}


def get_strings(lang: str) -> dict:
    return CATALOG.get(lang, CATALOG["en"])


def get_strategy_name(strategy_type: str, lang: str) -> str:
    return STRATEGY_NAMES.get(lang, STRATEGY_NAMES["en"])[strategy_type]


def get_strategy_blurb(strategy_type: str, lang: str) -> str:
    return STRATEGY_BLURBS.get(lang, STRATEGY_BLURBS["en"])[strategy_type]
