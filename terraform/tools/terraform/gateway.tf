# ============================================================================
# AgentCore Gateway - Research Tools
# ============================================================================

resource "aws_bedrockagentcore_gateway" "research_gateway" {
  name        = "${var.project_name}-research-tools-${local.suffix}"
  description = "Research Gateway with search and analysis tools"
  role_arn    = aws_iam_role.gateway_role.arn

  authorizer_type = "AWS_IAM"
  protocol_type   = "MCP"

  exception_level = "DEBUG"

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-research-tools-${local.suffix}"
    }
  )
}

# ============================================================================
# Gateway Targets: Tavily (2 targets)
# ============================================================================

resource "aws_bedrockagentcore_gateway_target" "tavily_search" {
  name               = "tavily-search"
  gateway_identifier = aws_bedrockagentcore_gateway.research_gateway.gateway_id
  description        = "Tavily AI-powered web search"

  credential_provider_configuration {
    gateway_iam_role {}
  }

  target_configuration {
    mcp {
      lambda {
        lambda_arn = aws_lambda_function.tavily.arn

        tool_schema {
          inline_payload {
            name        = "tavily_search"
            description = "AI-powered web search using Tavily. Returns up to 5 high-quality results with relevance scores."

            input_schema {
              type        = "object"
              description = "Search parameters"

              property {
                name        = "query"
                type        = "string"
                description = "Search query"
                required    = true
              }

              property {
                name        = "search_depth"
                type        = "string"
                description = "Search depth: 'basic' or 'advanced' (default: basic)"
              }

              property {
                name        = "topic"
                type        = "string"
                description = "Search topic: 'general' or 'news' (default: general)"
              }
            }
          }
        }
      }
    }
  }

  depends_on = [aws_lambda_function.tavily]
}

resource "aws_bedrockagentcore_gateway_target" "tavily_extract" {
  name               = "tavily-extract"
  gateway_identifier = aws_bedrockagentcore_gateway.research_gateway.gateway_id
  description        = "Tavily content extraction from URLs"

  credential_provider_configuration {
    gateway_iam_role {}
  }

  target_configuration {
    mcp {
      lambda {
        lambda_arn = aws_lambda_function.tavily.arn

        tool_schema {
          inline_payload {
            name        = "tavily_extract"
            description = "Extract clean content from web URLs using Tavily. Removes ads and boilerplate."

            input_schema {
              type        = "object"
              description = "Extraction parameters"

              property {
                name        = "urls"
                type        = "string"
                description = "Comma-separated URLs to extract content from"
                required    = true
              }

              property {
                name        = "extract_depth"
                type        = "string"
                description = "Extraction depth: 'basic' or 'advanced' (default: basic)"
              }
            }
          }
        }
      }
    }
  }

  depends_on = [aws_lambda_function.tavily]
}

# ============================================================================
# Gateway Targets: Wikipedia (2 targets)
# ============================================================================

resource "aws_bedrockagentcore_gateway_target" "wikipedia_search" {
  name               = "wikipedia-search"
  gateway_identifier = aws_bedrockagentcore_gateway.research_gateway.gateway_id
  description        = "Wikipedia article search"

  credential_provider_configuration {
    gateway_iam_role {}
  }

  target_configuration {
    mcp {
      lambda {
        lambda_arn = aws_lambda_function.wikipedia.arn

        tool_schema {
          inline_payload {
            name        = "wikipedia_search"
            description = "Search Wikipedia for articles. Returns up to 5 results with titles, snippets, and URLs."

            input_schema {
              type        = "object"
              description = "Search parameters"

              property {
                name        = "query"
                type        = "string"
                description = "Search query for Wikipedia articles"
                required    = true
              }
            }
          }
        }
      }
    }
  }

  depends_on = [aws_lambda_function.wikipedia]
}

resource "aws_bedrockagentcore_gateway_target" "wikipedia_get_article" {
  name               = "wikipedia-get-article"
  gateway_identifier = aws_bedrockagentcore_gateway.research_gateway.gateway_id
  description        = "Wikipedia article retrieval"

  credential_provider_configuration {
    gateway_iam_role {}
  }

  target_configuration {
    mcp {
      lambda {
        lambda_arn = aws_lambda_function.wikipedia.arn

        tool_schema {
          inline_payload {
            name        = "wikipedia_get_article"
            description = "Get full content of a specific Wikipedia article by title."

            input_schema {
              type        = "object"
              description = "Article retrieval parameters"

              property {
                name        = "title"
                type        = "string"
                description = "Exact title of the Wikipedia article"
                required    = true
              }

              property {
                name        = "summary_only"
                type        = "boolean"
                description = "If true, return only summary; if false, return full text (default: false)"
              }
            }
          }
        }
      }
    }
  }

  depends_on = [aws_lambda_function.wikipedia]
}

# ============================================================================
# Gateway Targets: DuckDuckGo (2 targets)
# ============================================================================

resource "aws_bedrockagentcore_gateway_target" "ddg_search" {
  name               = "ddg-search"
  gateway_identifier = aws_bedrockagentcore_gateway.research_gateway.gateway_id
  description        = "DuckDuckGo web search"

  credential_provider_configuration {
    gateway_iam_role {}
  }

  target_configuration {
    mcp {
      lambda {
        lambda_arn = aws_lambda_function.duckduckgo.arn

        tool_schema {
          inline_payload {
            name        = "ddg_search"
            description = "Search the web using DuckDuckGo. Returns up to 5 results with titles, snippets, and links."

            input_schema {
              type        = "object"
              description = "Search parameters"

              property {
                name        = "query"
                type        = "string"
                description = "Search query string"
                required    = true
              }
            }
          }
        }
      }
    }
  }

  depends_on = [aws_lambda_function.duckduckgo]
}

resource "aws_bedrockagentcore_gateway_target" "ddg_news" {
  name               = "ddg-news"
  gateway_identifier = aws_bedrockagentcore_gateway.research_gateway.gateway_id
  description        = "DuckDuckGo news search"

  credential_provider_configuration {
    gateway_iam_role {}
  }

  target_configuration {
    mcp {
      lambda {
        lambda_arn = aws_lambda_function.duckduckgo.arn

        tool_schema {
          inline_payload {
            name        = "ddg_news"
            description = "Search for recent news articles using DuckDuckGo News. Returns up to 5 results."

            input_schema {
              type        = "object"
              description = "News search parameters"

              property {
                name        = "query"
                type        = "string"
                description = "Search query string"
                required    = true
              }

              property {
                name        = "timelimit"
                type        = "string"
                description = "Time limit for news: 'd' (day), 'w' (week), 'm' (month)"
              }
            }
          }
        }
      }
    }
  }

  depends_on = [aws_lambda_function.duckduckgo]
}

# ============================================================================
# Gateway Targets: Google Search (2 targets)
# ============================================================================

resource "aws_bedrockagentcore_gateway_target" "google_web_search" {
  name               = "google-web-search"
  gateway_identifier = aws_bedrockagentcore_gateway.research_gateway.gateway_id
  description        = "Google web search"

  credential_provider_configuration {
    gateway_iam_role {}
  }

  target_configuration {
    mcp {
      lambda {
        lambda_arn = aws_lambda_function.google_search.arn

        tool_schema {
          inline_payload {
            name        = "google_web_search"
            description = "Search the web using Google Custom Search API. Returns up to 5 high-quality results."

            input_schema {
              type        = "object"
              description = "Search parameters"

              property {
                name        = "query"
                type        = "string"
                description = "Search query string"
                required    = true
              }
            }
          }
        }
      }
    }
  }

  depends_on = [aws_lambda_function.google_search]
}

resource "aws_bedrockagentcore_gateway_target" "google_image_search" {
  name               = "google-image-search"
  gateway_identifier = aws_bedrockagentcore_gateway.research_gateway.gateway_id
  description        = "Google image search"

  credential_provider_configuration {
    gateway_iam_role {}
  }

  target_configuration {
    mcp {
      lambda {
        lambda_arn = aws_lambda_function.google_search.arn

        tool_schema {
          inline_payload {
            name        = "google_image_search"
            description = "Search for images using Google's image search. Returns up to 5 verified accessible images."

            input_schema {
              type        = "object"
              description = "Image search parameters"

              property {
                name        = "query"
                type        = "string"
                description = "Search query for images"
                required    = true
              }
            }
          }
        }
      }
    }
  }

  depends_on = [aws_lambda_function.google_search]
}

# ============================================================================
# Gateway Targets: ArXiv (2 targets)
# ============================================================================

resource "aws_bedrockagentcore_gateway_target" "arxiv_search" {
  name               = "arxiv-search"
  gateway_identifier = aws_bedrockagentcore_gateway.research_gateway.gateway_id
  description        = "ArXiv paper search"

  credential_provider_configuration {
    gateway_iam_role {}
  }

  target_configuration {
    mcp {
      lambda {
        lambda_arn = aws_lambda_function.arxiv.arn

        tool_schema {
          inline_payload {
            name        = "arxiv_search"
            description = "Search for scientific papers on ArXiv. Returns up to 5 results with title, authors, abstract, and paper ID."

            input_schema {
              type        = "object"
              description = "Search parameters"

              property {
                name        = "query"
                type        = "string"
                description = "Search query for ArXiv papers"
                required    = true
              }
            }
          }
        }
      }
    }
  }

  depends_on = [aws_lambda_function.arxiv]
}

resource "aws_bedrockagentcore_gateway_target" "arxiv_get_paper" {
  name               = "arxiv-get-paper"
  gateway_identifier = aws_bedrockagentcore_gateway.research_gateway.gateway_id
  description        = "ArXiv paper retrieval"

  credential_provider_configuration {
    gateway_iam_role {}
  }

  target_configuration {
    mcp {
      lambda {
        lambda_arn = aws_lambda_function.arxiv.arn

        tool_schema {
          inline_payload {
            name        = "arxiv_get_paper"
            description = "Get full paper content from ArXiv by paper ID. Supports batch retrieval with comma-separated IDs."

            input_schema {
              type        = "object"
              description = "Paper retrieval parameters"

              property {
                name        = "paper_ids"
                type        = "string"
                description = "ArXiv paper ID or comma-separated IDs (e.g., '2308.08155' or '2308.08155,2401.12345')"
                required    = true
              }
            }
          }
        }
      }
    }
  }

  depends_on = [aws_lambda_function.arxiv]
}

# ============================================================================
# Gateway Targets: Finance (4 targets)
# ============================================================================

resource "aws_bedrockagentcore_gateway_target" "stock_quote" {
  name               = "stock-quote"
  gateway_identifier = aws_bedrockagentcore_gateway.research_gateway.gateway_id
  description        = "Stock quote data"

  credential_provider_configuration {
    gateway_iam_role {}
  }

  target_configuration {
    mcp {
      lambda {
        lambda_arn = aws_lambda_function.finance.arn

        tool_schema {
          inline_payload {
            name        = "stock_quote"
            description = "Get current stock quote with price, change, volume, and key metrics."

            input_schema {
              type        = "object"
              description = "Stock quote parameters"

              property {
                name        = "symbol"
                type        = "string"
                description = "Stock ticker symbol (e.g., AAPL, MSFT, TSLA)"
                required    = true
              }
            }
          }
        }
      }
    }
  }

  depends_on = [aws_lambda_function.finance]
}

resource "aws_bedrockagentcore_gateway_target" "stock_history" {
  name               = "stock-history"
  gateway_identifier = aws_bedrockagentcore_gateway.research_gateway.gateway_id
  description        = "Stock historical data"

  credential_provider_configuration {
    gateway_iam_role {}
  }

  target_configuration {
    mcp {
      lambda {
        lambda_arn = aws_lambda_function.finance.arn

        tool_schema {
          inline_payload {
            name        = "stock_history"
            description = "Get historical stock price data (OHLCV) over a specified time period."

            input_schema {
              type        = "object"
              description = "Historical data parameters"

              property {
                name        = "symbol"
                type        = "string"
                description = "Stock ticker symbol (e.g., AAPL, MSFT, TSLA)"
                required    = true
              }

              property {
                name        = "period"
                type        = "string"
                description = "Time period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max (default: 1mo)"
              }
            }
          }
        }
      }
    }
  }

  depends_on = [aws_lambda_function.finance]
}

resource "aws_bedrockagentcore_gateway_target" "financial_news" {
  name               = "financial-news"
  gateway_identifier = aws_bedrockagentcore_gateway.research_gateway.gateway_id
  description        = "Financial news articles"

  credential_provider_configuration {
    gateway_iam_role {}
  }

  target_configuration {
    mcp {
      lambda {
        lambda_arn = aws_lambda_function.finance.arn

        tool_schema {
          inline_payload {
            name        = "financial_news"
            description = "Get latest financial news articles for a stock symbol."

            input_schema {
              type        = "object"
              description = "News parameters"

              property {
                name        = "symbol"
                type        = "string"
                description = "Stock ticker symbol (e.g., AAPL, MSFT, TSLA)"
                required    = true
              }

              property {
                name        = "count"
                type        = "integer"
                description = "Number of news articles to return (1-20, default: 5)"
              }
            }
          }
        }
      }
    }
  }

  depends_on = [aws_lambda_function.finance]
}

resource "aws_bedrockagentcore_gateway_target" "stock_analysis" {
  name               = "stock-analysis"
  gateway_identifier = aws_bedrockagentcore_gateway.research_gateway.gateway_id
  description        = "Stock analysis and metrics"

  credential_provider_configuration {
    gateway_iam_role {}
  }

  target_configuration {
    mcp {
      lambda {
        lambda_arn = aws_lambda_function.finance.arn

        tool_schema {
          inline_payload {
            name        = "stock_analysis"
            description = "Get comprehensive stock analysis including valuation metrics, financial metrics, and analyst recommendations."

            input_schema {
              type        = "object"
              description = "Analysis parameters"

              property {
                name        = "symbol"
                type        = "string"
                description = "Stock ticker symbol (e.g., AAPL, MSFT, TSLA)"
                required    = true
              }
            }
          }
        }
      }
    }
  }

  depends_on = [aws_lambda_function.finance]
}
