#!/bin/bash

# AvalieImob Post-Deploy Test Script
# Testa a API após deployment no Railway

BASE_URL="https://avaliemob-production.up.railway.app"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🚀 AvalieImob API Test Suite${NC}\n"

# Test 1: Healthcheck
echo -e "${YELLOW}[1/5] Testing Healthcheck...${NC}"
HEALTH=$(curl -s -w "%{http_code}" -o /tmp/health.json "$BASE_URL/health")
if [ "$HEALTH" -eq 200 ]; then
  echo -e "${GREEN}✓ Healthcheck: OK${NC}"
  cat /tmp/health.json | jq .
else
  echo -e "${RED}✗ Healthcheck: FAILED (HTTP $HEALTH)${NC}"
  exit 1
fi

echo ""

# Test 2: Register User
echo -e "${YELLOW}[2/5] Testing User Registration...${NC}"
REGISTER=$(curl -s -X POST "$BASE_URL/api/trpc/auth.register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test_'$(date +%s)'@romatec.com",
    "password": "Test@123456"
  }')

echo "$REGISTER" | jq . 2>/dev/null
if echo "$REGISTER" | jq -e '.result.data.user' > /dev/null 2>&1; then
  echo -e "${GREEN}✓ Registration: OK${NC}"
else
  echo -e "${RED}✗ Registration: FAILED${NC}"
  echo "$REGISTER"
fi

echo ""

# Test 3: Login
echo -e "${YELLOW}[3/5] Testing Login...${NC}"
LOGIN=$(curl -s -X POST "$BASE_URL/api/trpc/auth.login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jose@romatec.com",
    "password": "Teste@123"
  }')

TOKEN=$(echo "$LOGIN" | jq -r '.result.data.token' 2>/dev/null)
if [ -n "$TOKEN" ] && [ "$TOKEN" != "null" ]; then
  echo -e "${GREEN}✓ Login: OK${NC}"
  echo "Token: ${TOKEN:0:20}..."
else
  echo -e "${YELLOW}⚠ Login: User not found (expected on fresh install)${NC}"
fi

echo ""

# Test 4: Frontend
echo -e "${YELLOW}[4/5] Testing Frontend Load...${NC}"
FRONTEND=$(curl -s -w "%{http_code}" -o /tmp/index.html "$BASE_URL/")
if [ "$FRONTEND" -eq 200 ]; then
  SIZE=$(wc -c < /tmp/index.html)
  echo -e "${GREEN}✓ Frontend: OK ($SIZE bytes)${NC}"
else
  echo -e "${RED}✗ Frontend: FAILED (HTTP $FRONTEND)${NC}"
fi

echo ""

# Test 5: API Response Time
echo -e "${YELLOW}[5/5] Testing API Response Time...${NC}"
TIME=$(curl -s -w "%{time_total}" -o /dev/null "$BASE_URL/health")
echo -e "${GREEN}✓ Response Time: ${TIME}s${NC}"

echo ""
echo -e "${GREEN}✅ All tests completed!${NC}"
echo ""
echo "📊 Next steps:"
echo "  1. Visit: https://avaliemob-production.up.railway.app"
echo "  2. Create account and test full workflow"
echo "  3. Check browser console for errors"
echo "  4. Run database migrations if needed"
