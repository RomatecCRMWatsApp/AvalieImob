#!/usr/bin/env python3
"""
RomaTec AvalieImob Backend API Comprehensive Test Suite
Tests all endpoints in the specified order with proper authentication flow.
"""

import requests
import json
import uuid
from datetime import datetime
import time

# Base URL from frontend .env + /api prefix
BASE_URL = "https://review-simples.preview.emergentagent.com/api"

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.failures = []
        
    def assert_response(self, response, expected_status, test_name, expected_keys=None):
        """Assert response status and optionally check for expected keys"""
        try:
            if response.status_code != expected_status:
                self.failed += 1
                error_msg = f"❌ {test_name}: Expected {expected_status}, got {response.status_code}"
                if response.text:
                    try:
                        error_detail = response.json().get('detail', response.text[:200])
                        error_msg += f" - {error_detail}"
                    except:
                        error_msg += f" - {response.text[:200]}"
                self.failures.append(error_msg)
                print(error_msg)
                return False
            
            if expected_keys and response.status_code < 400:
                try:
                    data = response.json()
                    for key in expected_keys:
                        if key not in data:
                            self.failed += 1
                            error_msg = f"❌ {test_name}: Missing key '{key}' in response"
                            self.failures.append(error_msg)
                            print(error_msg)
                            return False
                except:
                    self.failed += 1
                    error_msg = f"❌ {test_name}: Invalid JSON response"
                    self.failures.append(error_msg)
                    print(error_msg)
                    return False
            
            self.passed += 1
            print(f"✅ {test_name}")
            return True
            
        except Exception as e:
            self.failed += 1
            error_msg = f"❌ {test_name}: Exception - {str(e)}"
            self.failures.append(error_msg)
            print(error_msg)
            return False
    
    def print_summary(self):
        print(f"\n{'='*60}")
        print(f"TEST SUMMARY: {self.passed} passed, {self.failed} failed")
        if self.failures:
            print(f"\nFAILURES:")
            for failure in self.failures:
                print(f"  {failure}")
        print(f"{'='*60}")

def test_romatec_backend():
    """Main test function following the specified test order"""
    results = TestResults()
    
    # Test data storage
    auth_token = None
    user_id = None
    client_id = None
    property_id = None
    evaluation_id = None
    sample_id = None
    
    # Second user for isolation testing
    auth_token_2 = None
    
    print(f"🚀 Starting RomaTec AvalieImob Backend Tests")
    print(f"Base URL: {BASE_URL}")
    print(f"{'='*60}")
    
    # ===== 1. AUTH FLOW (HIGH PRIORITY) =====
    print("\n📋 1. AUTH FLOW TESTS")
    
    # 1.1 Register new user
    register_data = {
        "name": "Test User",
        "email": "test@romatec.com",
        "password": "senha123",
        "role": "Engenheiro Avaliador",
        "crea": "CREA-MA 99999"
    }
    
    response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
    if results.assert_response(response, 200, "Register new user", ["user", "token"]):
        data = response.json()
        auth_token = data["token"]
        user_id = data["user"]["id"]
        print(f"   User ID: {user_id}")
        print(f"   Token: {auth_token[:20]}...")
    
    # 1.2 Register same email again (should fail)
    response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
    results.assert_response(response, 400, "Register duplicate email (should fail)")
    
    # 1.3 Login with correct credentials
    login_data = {"email": "test@romatec.com", "password": "senha123"}
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    if results.assert_response(response, 200, "Login with correct credentials", ["user", "token"]):
        data = response.json()
        auth_token = data["token"]  # Update token
    
    # 1.4 Login with wrong password
    wrong_login = {"email": "test@romatec.com", "password": "wrongpass"}
    response = requests.post(f"{BASE_URL}/auth/login", json=wrong_login)
    results.assert_response(response, 401, "Login with wrong password (should fail)")
    
    # 1.5 Get user info with token
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    results.assert_response(response, 200, "Get user info with token", ["id", "name", "email"])
    
    # 1.6 Get user info without token
    response = requests.get(f"{BASE_URL}/auth/me")
    results.assert_response(response, 401, "Get user info without token (should fail)")
    
    # 1.7 Update user profile
    update_data = {"name": "Updated Name", "bio": "Engenheiro com 10 anos"}
    response = requests.put(f"{BASE_URL}/auth/me", json=update_data, headers=headers)
    if results.assert_response(response, 200, "Update user profile", ["name", "bio"]):
        data = response.json()
        if data.get("name") != "Updated Name":
            results.failed += 1
            results.failures.append("❌ Update user profile: Name not updated correctly")
    
    # ===== 2. CLIENTS CRUD (HIGH PRIORITY) =====
    print("\n📋 2. CLIENTS CRUD TESTS")
    
    # 2.1 Get empty clients list
    response = requests.get(f"{BASE_URL}/clients", headers=headers)
    if results.assert_response(response, 200, "Get empty clients list"):
        data = response.json()
        if len(data) != 0:
            print(f"   Warning: Expected empty list, got {len(data)} items")
    
    # 2.2 Create first client (Pessoa Jurídica)
    client_data = {
        "name": "Banco XYZ",
        "type": "Pessoa Jurídica",
        "doc": "00.000.000/0001-00",
        "phone": "(98) 1234-5678",
        "email": "pj@xyz.com",
        "city": "São Luís/MA"
    }
    response = requests.post(f"{BASE_URL}/clients", json=client_data, headers=headers)
    if results.assert_response(response, 200, "Create client (Pessoa Jurídica)", ["id", "name", "type"]):
        data = response.json()
        client_id = data["id"]
        print(f"   Client ID: {client_id}")
    
    # 2.3 Create second client (Pessoa Física)
    client_data_2 = {
        "name": "João Silva",
        "type": "Pessoa Física",
        "doc": "123.456.789-00",
        "phone": "(98) 9876-5432",
        "email": "joao@email.com",
        "city": "São Luís/MA"
    }
    response = requests.post(f"{BASE_URL}/clients", json=client_data_2, headers=headers)
    results.assert_response(response, 200, "Create client (Pessoa Física)", ["id", "name", "type"])
    
    # 2.4 Get clients list (should have 2)
    response = requests.get(f"{BASE_URL}/clients", headers=headers)
    if results.assert_response(response, 200, "Get clients list (should have 2)"):
        data = response.json()
        if len(data) != 2:
            results.failed += 1
            results.failures.append(f"❌ Get clients list: Expected 2 clients, got {len(data)}")
    
    # 2.5 Update client
    update_client_data = {"name": "Banco XYZ Atualizado", "phone": "(98) 1111-2222"}
    response = requests.put(f"{BASE_URL}/clients/{client_id}", json=update_client_data, headers=headers)
    if results.assert_response(response, 200, "Update client", ["name"]):
        data = response.json()
        if data.get("name") != "Banco XYZ Atualizado":
            results.failed += 1
            results.failures.append("❌ Update client: Name not updated correctly")
    
    # 2.6 Delete client
    response = requests.delete(f"{BASE_URL}/clients/{client_id}", headers=headers)
    results.assert_response(response, 200, "Delete client", ["ok"])
    
    # 2.7 Verify client deleted
    response = requests.get(f"{BASE_URL}/clients", headers=headers)
    if results.assert_response(response, 200, "Verify client deleted"):
        data = response.json()
        if len(data) != 1:
            results.failed += 1
            results.failures.append(f"❌ Verify client deleted: Expected 1 client, got {len(data)}")
    
    # ===== 3. PROPERTIES CRUD (HIGH PRIORITY) =====
    print("\n📋 3. PROPERTIES CRUD TESTS")
    
    # Get remaining client ID for property tests
    response = requests.get(f"{BASE_URL}/clients", headers=headers)
    if response.status_code == 200:
        clients = response.json()
        if clients:
            client_id = clients[0]["id"]
    
    # 3.1 Create urban property
    property_data = {
        "ref": "APT-001",
        "client_id": client_id,
        "type": "Urbano",
        "subtype": "Apartamento",
        "address": "Rua X, 100",
        "city": "São Luís",
        "area": 85,
        "built_area": 85,
        "value": 380000,
        "status": "Rascunho"
    }
    response = requests.post(f"{BASE_URL}/properties", json=property_data, headers=headers)
    if results.assert_response(response, 200, "Create urban property", ["id", "ref", "type"]):
        data = response.json()
        property_id = data["id"]
        print(f"   Property ID: {property_id}")
    
    # 3.2 Create rural property
    rural_property = {
        "ref": "RURAL-001",
        "client_id": client_id,
        "type": "Rural",
        "subtype": "Fazenda",
        "address": "Zona Rural",
        "city": "Bacabal",
        "area": 1000,
        "built_area": 200,
        "value": 2000000,
        "status": "Rascunho"
    }
    response = requests.post(f"{BASE_URL}/properties", json=rural_property, headers=headers)
    results.assert_response(response, 200, "Create rural property", ["id", "type"])
    
    # 3.3 Create guarantee property
    guarantee_property = {
        "ref": "GAR-001",
        "client_id": client_id,
        "type": "Garantia",
        "subtype": "Safra de Soja",
        "address": "Fazenda São João",
        "city": "Balsas",
        "area": 500,
        "built_area": 0,
        "value": 1500000,
        "status": "Rascunho"
    }
    response = requests.post(f"{BASE_URL}/properties", json=guarantee_property, headers=headers)
    results.assert_response(response, 200, "Create guarantee property", ["id", "type"])
    
    # 3.4 Get all properties (should have 3)
    response = requests.get(f"{BASE_URL}/properties", headers=headers)
    if results.assert_response(response, 200, "Get all properties (should have 3)"):
        data = response.json()
        if len(data) != 3:
            results.failed += 1
            results.failures.append(f"❌ Get all properties: Expected 3 properties, got {len(data)}")
    
    # 3.5 Filter properties by type
    response = requests.get(f"{BASE_URL}/properties?type=Urbano", headers=headers)
    if results.assert_response(response, 200, "Filter properties by type (Urbano)"):
        data = response.json()
        if len(data) != 1:
            results.failed += 1
            results.failures.append(f"❌ Filter properties: Expected 1 urban property, got {len(data)}")
    
    # 3.6 Update property
    update_property = {"value": 400000, "status": "Em Análise"}
    response = requests.put(f"{BASE_URL}/properties/{property_id}", json=update_property, headers=headers)
    if results.assert_response(response, 200, "Update property", ["value", "status"]):
        data = response.json()
        if data.get("value") != 400000:
            results.failed += 1
            results.failures.append("❌ Update property: Value not updated correctly")
    
    # 3.7 Delete property
    response = requests.delete(f"{BASE_URL}/properties/{property_id}", headers=headers)
    results.assert_response(response, 200, "Delete property", ["ok"])
    
    # ===== 4. SAMPLES (MEDIUM PRIORITY) =====
    print("\n📋 4. SAMPLES TESTS")
    
    # 4.1 Create sample with auto price calculation
    sample_data = {
        "ref": "AM-001",
        "type": "Apartamento",
        "area": 90,
        "value": 420000,
        "source": "OLX",
        "neighborhood": "Calhau"
    }
    response = requests.post(f"{BASE_URL}/samples", json=sample_data, headers=headers)
    if results.assert_response(response, 200, "Create sample with auto price calculation", ["id", "price_per_sqm"]):
        data = response.json()
        sample_id = data["id"]
        expected_price_per_sqm = round(420000 / 90)  # 4667
        if data.get("price_per_sqm") != expected_price_per_sqm:
            results.failed += 1
            results.failures.append(f"❌ Sample price calculation: Expected {expected_price_per_sqm}, got {data.get('price_per_sqm')}")
        else:
            print(f"   ✅ Price per sqm calculated correctly: {data.get('price_per_sqm')}")
    
    # 4.2 Get samples list
    response = requests.get(f"{BASE_URL}/samples", headers=headers)
    if results.assert_response(response, 200, "Get samples list"):
        data = response.json()
        if len(data) != 1:
            results.failed += 1
            results.failures.append(f"❌ Get samples: Expected 1 sample, got {len(data)}")
    
    # ===== 5. EVALUATIONS (HIGH PRIORITY - AUTO CODE GENERATION) =====
    print("\n📋 5. EVALUATIONS TESTS")
    
    # Get a property ID for evaluation tests
    response = requests.get(f"{BASE_URL}/properties", headers=headers)
    if response.status_code == 200:
        properties = response.json()
        if properties:
            property_id = properties[0]["id"]
    
    # 5.1 Create PTAM evaluation
    ptam_data = {
        "type": "PTAM",
        "method": "Comparativo Direto",
        "client_id": client_id,
        "property_id": property_id,
        "value": 380000
    }
    response = requests.post(f"{BASE_URL}/evaluations", json=ptam_data, headers=headers)
    if results.assert_response(response, 200, "Create PTAM evaluation", ["id", "code"]):
        data = response.json()
        evaluation_id = data["id"]
        code = data.get("code", "")
        if not code.startswith("PTAM-2026-001"):
            results.failed += 1
            results.failures.append(f"❌ PTAM code generation: Expected PTAM-2026-001, got {code}")
        else:
            print(f"   ✅ PTAM code generated correctly: {code}")
    
    # 5.2 Create Laudo evaluation
    laudo_data = {
        "type": "Laudo",
        "method": "Comparativo Direto",
        "client_id": client_id,
        "property_id": property_id,
        "value": 380000
    }
    response = requests.post(f"{BASE_URL}/evaluations", json=laudo_data, headers=headers)
    if results.assert_response(response, 200, "Create Laudo evaluation", ["id", "code"]):
        data = response.json()
        code = data.get("code", "")
        if not code.startswith("LAU-2026-002"):
            results.failed += 1
            results.failures.append(f"❌ Laudo code generation: Expected LAU-2026-002, got {code}")
        else:
            print(f"   ✅ Laudo code generated correctly: {code}")
    
    # 5.3 Create Garantia Safra evaluation
    garantia_data = {
        "type": "Garantia Safra",
        "method": "Comparativo Direto",
        "client_id": client_id,
        "property_id": property_id,
        "value": 1500000
    }
    response = requests.post(f"{BASE_URL}/evaluations", json=garantia_data, headers=headers)
    if results.assert_response(response, 200, "Create Garantia Safra evaluation", ["id", "code"]):
        data = response.json()
        code = data.get("code", "")
        if not code.startswith("GAR-2026-003"):
            results.failed += 1
            results.failures.append(f"❌ Garantia code generation: Expected GAR-2026-003, got {code}")
        else:
            print(f"   ✅ Garantia code generated correctly: {code}")
    
    # 5.4 Get evaluations list
    response = requests.get(f"{BASE_URL}/evaluations", headers=headers)
    if results.assert_response(response, 200, "Get evaluations list"):
        data = response.json()
        if len(data) != 3:
            results.failed += 1
            results.failures.append(f"❌ Get evaluations: Expected 3 evaluations, got {len(data)}")
    
    # 5.5 Update evaluation status
    update_eval = {"status": "Emitido"}
    response = requests.put(f"{BASE_URL}/evaluations/{evaluation_id}", json=update_eval, headers=headers)
    if results.assert_response(response, 200, "Update evaluation status", ["status"]):
        data = response.json()
        if data.get("status") != "Emitido":
            results.failed += 1
            results.failures.append("❌ Update evaluation: Status not updated correctly")
    
    # ===== 6. DASHBOARD STATS (MEDIUM PRIORITY) =====
    print("\n📋 6. DASHBOARD STATS TESTS")
    
    response = requests.get(f"{BASE_URL}/dashboard/stats", headers=headers)
    if results.assert_response(response, 200, "Get dashboard stats", ["evaluations", "clients", "properties", "revenue", "monthly"]):
        data = response.json()
        if len(data.get("monthly", [])) != 6:
            results.failed += 1
            results.failures.append(f"❌ Dashboard stats: Expected 6 monthly items, got {len(data.get('monthly', []))}")
        else:
            print(f"   ✅ Dashboard stats: {data.get('evaluations')} evaluations, {data.get('clients')} clients, {data.get('properties')} properties")
    
    # ===== 7. AI CHAT - MULTI-TURN TEST (HIGH PRIORITY) =====
    print("\n📋 7. AI CHAT MULTI-TURN TESTS")
    
    # Generate unique session ID
    session_id = f"test_session_{int(time.time())}"
    print(f"   Using session ID: {session_id}")
    
    # 7.1 First AI message
    ai_data_1 = {
        "session_id": session_id,
        "message": "Olá, sou um engenheiro avaliador. Pode me ajudar com um PTAM?"
    }
    response = requests.post(f"{BASE_URL}/ai/chat", json=ai_data_1, headers=headers)
    if results.assert_response(response, 200, "AI Chat - First message", ["session_id", "reply"]):
        data = response.json()
        print(f"   AI Reply 1: {data.get('reply', '')[:100]}...")
    
    # 7.2 Second AI message (contextual)
    ai_data_2 = {
        "session_id": session_id,
        "message": "Qual norma da ABNT devo citar?"
    }
    response = requests.post(f"{BASE_URL}/ai/chat", json=ai_data_2, headers=headers)
    if results.assert_response(response, 200, "AI Chat - Second message (contextual)", ["session_id", "reply"]):
        data = response.json()
        reply = data.get('reply', '')
        print(f"   AI Reply 2: {reply[:100]}...")
        # Check if AI mentions NBR 14.653 (contextual response)
        if "NBR" not in reply and "14.653" not in reply:
            print(f"   ⚠️  Warning: AI response may not be contextual (no NBR mention)")
    
    # 7.3 Third AI message (technical generation)
    ai_data_3 = {
        "session_id": session_id,
        "message": "Gere uma fundamentação técnica curta para um apartamento de 85m²"
    }
    response = requests.post(f"{BASE_URL}/ai/chat", json=ai_data_3, headers=headers)
    if results.assert_response(response, 200, "AI Chat - Third message (technical)", ["session_id", "reply"]):
        data = response.json()
        reply = data.get('reply', '')
        print(f"   AI Reply 3: {reply[:100]}...")
        # Check if response is in Portuguese
        portuguese_indicators = ["apartamento", "área", "técnica", "avaliação", "imóvel"]
        if not any(word in reply.lower() for word in portuguese_indicators):
            print(f"   ⚠️  Warning: AI response may not be in Portuguese")
    
    # 7.4 Get AI conversation history
    response = requests.get(f"{BASE_URL}/ai/history/{session_id}", headers=headers)
    if results.assert_response(response, 200, "Get AI conversation history"):
        data = response.json()
        if len(data) != 6:  # 3 user + 3 assistant messages
            results.failed += 1
            results.failures.append(f"❌ AI history: Expected 6 messages, got {len(data)}")
        else:
            print(f"   ✅ AI history: {len(data)} messages in chronological order")
            # Verify message order
            roles = [msg.get("role") for msg in data]
            expected_roles = ["user", "assistant", "user", "assistant", "user", "assistant"]
            if roles != expected_roles:
                results.failed += 1
                results.failures.append(f"❌ AI history order: Expected {expected_roles}, got {roles}")
    
    # ===== 8. SUBSCRIPTION (LOW PRIORITY) =====
    print("\n📋 8. SUBSCRIPTION TESTS")
    
    # 8.1 Get subscription info
    response = requests.get(f"{BASE_URL}/subscription", headers=headers)
    results.assert_response(response, 200, "Get subscription info", ["plan", "next_billing", "status"])
    
    # 8.2 Change subscription plan
    plan_data = {"plan_id": "anual"}
    response = requests.post(f"{BASE_URL}/subscription/change", json=plan_data, headers=headers)
    if results.assert_response(response, 200, "Change subscription plan", ["ok", "plan"]):
        data = response.json()
        if data.get("plan") != "anual":
            results.failed += 1
            results.failures.append("❌ Change subscription: Plan not updated correctly")
    
    # ===== 9. DATA ISOLATION (HIGH PRIORITY) =====
    print("\n📋 9. DATA ISOLATION TESTS")
    
    # 9.1 Register second user
    register_data_2 = {
        "name": "Second User",
        "email": "second@romatec.com",
        "password": "senha456",
        "role": "Corretor",
        "crea": "CREA-MA 88888"
    }
    response = requests.post(f"{BASE_URL}/auth/register", json=register_data_2)
    if results.assert_response(response, 200, "Register second user", ["user", "token"]):
        data = response.json()
        auth_token_2 = data["token"]
    
    # 9.2 Login as second user
    login_data_2 = {"email": "second@romatec.com", "password": "senha456"}
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data_2)
    if results.assert_response(response, 200, "Login as second user", ["user", "token"]):
        data = response.json()
        auth_token_2 = data["token"]
    
    # 9.3 Check data isolation - clients
    headers_2 = {"Authorization": f"Bearer {auth_token_2}"}
    response = requests.get(f"{BASE_URL}/clients", headers=headers_2)
    if results.assert_response(response, 200, "Data isolation - clients"):
        data = response.json()
        if len(data) != 0:
            results.failed += 1
            results.failures.append(f"❌ Data isolation - clients: Expected 0 clients for second user, got {len(data)}")
        else:
            print(f"   ✅ Data isolation verified: Second user sees 0 clients")
    
    # 9.4 Check data isolation - evaluations
    response = requests.get(f"{BASE_URL}/evaluations", headers=headers_2)
    if results.assert_response(response, 200, "Data isolation - evaluations"):
        data = response.json()
        if len(data) != 0:
            results.failed += 1
            results.failures.append(f"❌ Data isolation - evaluations: Expected 0 evaluations for second user, got {len(data)}")
        else:
            print(f"   ✅ Data isolation verified: Second user sees 0 evaluations")
    
    # Print final summary
    results.print_summary()
    
    return results

if __name__ == "__main__":
    test_results = test_romatec_backend()
    
    # Exit with error code if tests failed
    if test_results.failed > 0:
        exit(1)
    else:
        print("\n🎉 All tests passed!")
        exit(0)