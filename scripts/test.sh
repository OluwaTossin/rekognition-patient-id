#!/bin/bash
# Test script for the Patient Identity Verification System

set -e

# Configuration
API_URL=${API_URL:-"https://your-api-id.execute-api.us-east-1.amazonaws.com/prod"}
TEST_PATIENT_ID="P-TEST-$(date +%s)"

echo "🧪 Testing Patient Identity Verification System"
echo "================================================"

# Check if required files exist
if [ ! -f "patient1.jpg" ]; then
    echo "❌ Test image patient1.jpg not found"
    exit 1
fi

if [ ! -f "patient1_checkin.jpg" ]; then
    echo "ℹ️  Using patient1.jpg for both registration and check-in"
    cp patient1.jpg patient1_checkin.jpg
fi

echo "📋 Test Configuration:"
echo "  - API URL: $API_URL"
echo "  - Test Patient ID: $TEST_PATIENT_ID"
echo ""

# Test 1: Register Patient
echo "🏥 Test 1: Patient Registration"
echo "--------------------------------"

# Convert image to base64
IMG_B64=$(base64 -w 0 patient1.jpg)

# Register patient
echo "📤 Registering patient..."
REGISTER_RESPONSE=$(curl -s -X POST "$API_URL/patients/register" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "'"$TEST_PATIENT_ID"'",
    "attributes": {
      "name": "Test Patient",
      "dob": "1990-01-01",
      "phone": "+1234567890",
      "email": "test@example.com",
      "appointment_id": "APT-TEST-001"
    },
    "image_base64": "'"$IMG_B64"'"
  }')

echo "📥 Registration Response:"
echo "$REGISTER_RESPONSE" | jq '.' 2>/dev/null || echo "$REGISTER_RESPONSE"

# Check if registration was successful
if echo "$REGISTER_RESPONSE" | grep -q "face_id"; then
    echo "✅ Registration successful!"
else
    echo "❌ Registration failed!"
    exit 1
fi

echo ""

# Test 2: Identify Patient
echo "🔍 Test 2: Patient Identification"
echo "----------------------------------"

# Convert check-in image to base64
CHECKIN_B64=$(base64 -w 0 patient1_checkin.jpg)

# Wait a moment for DynamoDB consistency
echo "⏳ Waiting for data consistency..."
sleep 2

# Identify patient
echo "📤 Identifying patient..."
IDENTIFY_RESPONSE=$(curl -s -X POST "$API_URL/patients/identify" \
  -H "Content-Type: application/json" \
  -d '{
    "image_base64": "'"$CHECKIN_B64"'"
  }')

echo "📥 Identification Response:"
echo "$IDENTIFY_RESPONSE" | jq '.' 2>/dev/null || echo "$IDENTIFY_RESPONSE"

# Check if identification was successful
if echo "$IDENTIFY_RESPONSE" | grep -q "similarity"; then
    echo "✅ Identification successful!"
    SIMILARITY=$(echo "$IDENTIFY_RESPONSE" | jq -r '.similarity' 2>/dev/null || echo "N/A")
    echo "🎯 Similarity Score: $SIMILARITY%"
else
    echo "❌ Identification failed!"
fi

echo ""

# Test 3: Error Handling
echo "🚨 Test 3: Error Handling"
echo "--------------------------"

# Test with invalid image data
echo "📤 Testing with invalid image..."
ERROR_RESPONSE=$(curl -s -X POST "$API_URL/patients/identify" \
  -H "Content-Type: application/json" \
  -d '{
    "image_base64": "invalid_base64_data"
  }')

echo "📥 Error Response:"
echo "$ERROR_RESPONSE" | jq '.' 2>/dev/null || echo "$ERROR_RESPONSE"

if echo "$ERROR_RESPONSE" | grep -q "error"; then
    echo "✅ Error handling working correctly!"
else
    echo "⚠️  Error handling may need attention"
fi

echo ""

# Test 4: Performance Test
echo "⚡ Test 4: Performance Test"
echo "---------------------------"

echo "📊 Running 5 identification requests..."
TOTAL_TIME=0

for i in {1..5}; do
    START_TIME=$(date +%s%N)
    
    curl -s -X POST "$API_URL/patients/identify" \
      -H "Content-Type: application/json" \
      -d '{
        "image_base64": "'"$CHECKIN_B64"'"
      }' > /dev/null
    
    END_TIME=$(date +%s%N)
    DURATION=$((($END_TIME - $START_TIME) / 1000000))
    TOTAL_TIME=$(($TOTAL_TIME + $DURATION))
    
    echo "  Request $i: ${DURATION}ms"
done

AVERAGE_TIME=$(($TOTAL_TIME / 5))
echo "📈 Average Response Time: ${AVERAGE_TIME}ms"

if [ $AVERAGE_TIME -lt 2000 ]; then
    echo "✅ Performance acceptable (< 2s)"
else
    echo "⚠️  Performance may need optimization (> 2s)"
fi

echo ""
echo "🎉 Testing Complete!"
echo "===================="
echo ""
echo "📊 Test Summary:"
echo "  - Registration: $(echo "$REGISTER_RESPONSE" | grep -q "face_id" && echo "✅ PASS" || echo "❌ FAIL")"
echo "  - Identification: $(echo "$IDENTIFY_RESPONSE" | grep -q "similarity" && echo "✅ PASS" || echo "❌ FAIL")"
echo "  - Error Handling: $(echo "$ERROR_RESPONSE" | grep -q "error" && echo "✅ PASS" || echo "⚠️  CHECK")"
echo "  - Performance: $([ $AVERAGE_TIME -lt 2000 ] && echo "✅ GOOD" || echo "⚠️  SLOW")"
echo ""
echo "📚 Next Steps:"
echo "  - Check CloudWatch logs for detailed execution info"
echo "  - Monitor DynamoDB and Rekognition usage"
echo "  - Test with different image qualities and angles"
echo "  - Set up automated monitoring and alerts"