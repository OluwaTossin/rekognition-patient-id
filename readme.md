# AI in Healthcare: Patient Identity Verification with Rekognition and DynamoDB

## 📖 Introduction
This project demonstrates how to design and implement a production-grade, serverless pipeline for **patient identification** using **Amazon Rekognition**, **API Gateway**, **AWS Lambda**, and **DynamoDB**.  
Healthcare providers can register patients with facial images at the time of appointment scheduling, then identify them instantly during check-in by matching new photos against a secure Rekognition collection.  

The goal: improve efficiency, reduce errors, and enhance patient experience while keeping the solution **serverless, scalable, and cost-effective (AWS Free Tier friendly).**

---

## 🏥 Case Study & Business Challenge
**Enterprise Healthcare – Cleveland Medical Center (CMC).**  
CMC is rolling out a “home-nearby first” model with remote triage, local clinics, and rapid check-in.  

**Problem:** Current appointment portal uses numeric IDs, requiring staff to reconcile IDs with patients at busy clinics. This causes delays and occasional mismatches.  

**Requirement:** Augment check-in with **face-based identification** to:
- Speed triage 🚀  
- Reduce mismatches 🔒  
- Link the correct medical record at first contact 🗂  

**Constraints:**  
- Health data & biometrics demand strict **privacy, consent, and auditability**.  
- Must be low-cost, cloud-native, and production-ready (IAM least privilege, encryption, monitoring, throttling, traceability).  

---

## 💡 Solution Overview
1. **Registration:**  
   Patients upload a photo and metadata → Rekognition indexes the face → DynamoDB stores demographics + `face_id`.  

2. **Check-in (Identify):**  
   Patients upload a fresh photo → Rekognition `SearchFacesByImage` finds a match → DynamoDB query retrieves patient details.  

**Core AWS Services Used:**  
- API Gateway (public API endpoints)  
- Lambda (serverless functions for register/identify)  
- Rekognition (face collection, index/search)  
- DynamoDB (patient metadata with GSI for `face_id`)  
- CloudWatch (logs and monitoring)  

---

## 🏗 Architecture Diagram
*(Insert your architecture diagram image here)*

![alt text](Arch.png)
---

## ✨ Executive Summary (TL;DR)
This project shows how **AI can simplify patient check-in** at hospitals and clinics. Instead of relying on appointment numbers or ID cards, patients are identified instantly by their face.  

We built a secure, low-cost system on AWS that:  
- Registers new patients by storing their photo + details  
- Recognizes returning patients with near-perfect accuracy  
- Uses **Amazon Rekognition** for AI facial recognition  
- Uses **DynamoDB** for patient records  
- Runs fully serverless with **Lambda** + **API Gateway**  

Result: **efficient, error-free, scalable healthcare identity verification**.  

---

## 📊 Data Model
**DynamoDB Table: `cmc_patients`**

- **PK**: `patient_id` (string)  
- **Attributes**: `appointment_id`, `name`, `dob`, `phone`, `face_id`, `created_at`, `updated_at`  
- **GSI**: `face_id-index` (PK = `face_id`) for fast lookup by Rekognition match results  

---

## ⚙️ Implementation Phases

### **Phase 1 — Setup**
- Create a Rekognition **Face Collection** (`cmc-reko-lab-dev-faces`)  
- Provision a DynamoDB table (`cmc_patients`) with **GSI** for `face_id`  

---

### **Phase 2 — IAM Roles**
- Create a Lambda execution role with least privilege:  
  - Rekognition: `IndexFaces`, `SearchFacesByImage`  
  - DynamoDB: `PutItem`, `Query`  
  - CloudWatch Logs: `CreateLogGroup`, `CreateLogStream`, `PutLogEvents`  

---

### **Phase 3 — Lambda Functions**
- **Register Function (`register_patient.py`)**  
  - Decodes base64 image, calls `IndexFaces`, stores patient details in DynamoDB.  
- **Identify Function (`identify_patient.py`)**  
  - Runs `SearchFacesByImage`, retrieves matched record from DynamoDB, returns details + similarity score.  

---

### **Phase 4 — API Gateway**
- Routes:  
  - `POST /patients/register` → `register_patient` Lambda  
  - `POST /patients/identify` → `identify_patient` Lambda  
- Permissions: API Gateway invokes Lambda securely via resource policy.  

---

### **Phase 5 — Observability**
- CloudWatch Logs enabled for each Lambda.  
- Logs capture runtime, exceptions, and Rekognition/DynamoDB responses.  

---

### **Phase 6 — Test Calls**

#### Register a patient
```bash
IMG=patient1.jpg
B64=$(base64 -w 0 "$IMG")

curl -s -X POST "$URL/prod/patients/register" \
  -H "Content-Type: application/json" \
  -d '{
        "patient_id": "P-1001",
        "attributes": { "name": "Ada Okafor", "dob": "1991-03-22", "phone": "+2348012345678" },
        "image_base64": "'"$B64"'"
      }' | jq

