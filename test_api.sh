#!/bin/bash

# API base URL
BASE_URL="http://localhost:8000/api"
DOC_PATH="doc/1706.03762v7.pdf"

# 1. Upload a document
echo "Uploading document..."
UPLOAD_RESPONSE=$(curl -s -X POST "$BASE_URL/documents/upload" \
  -H "accept: application/json" \
  -F "file=@$DOC_PATH;type=application/pdf")

echo "Upload response: $UPLOAD_RESPONSE"

# Extract document_id manually using grep/sed (simple approach)
DOCUMENT_ID=$(echo "$UPLOAD_RESPONSE" | grep -o '"id":[0-9]*' | grep -o '[0-9]*')

echo "Document ID: $DOCUMENT_ID"

# 2. Wait until document processing is completed
echo "Waiting for document processing to complete..."
STATUS=""

while [ "$STATUS" != "completed" ]; do
  sleep 2
  # Fetch the document JSON
  RESPONSE=$(curl -s "$BASE_URL/documents/$DOCUMENT_ID" -H "accept: application/json")
  
  # Extract the "status" value reliably
  STATUS=$(echo "$RESPONSE" | awk -F'"status":"' '{print $2}' | awk -F'"' '{print $1}')
  
  echo "Current status: $STATUS"
done

echo "Document processing completed!"

# 3. Retrieve document details
echo "Retrieving document details..."
curl -s "$BASE_URL/documents/$DOCUMENT_ID" -H "accept: application/json"

# 4. Perform chat/QA query
echo "Performing chat query..."
curl -s -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d "{\"document_id\":\"$DOCUMENT_ID\",\"message\":\"What is the main conclusion of this paper?\"}"
