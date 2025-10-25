## SECTION 1 : PROJECT TITLE
## IRS-PM-2025-10-26-AIS07FT-GRP5-MyTrail

### Business Video

[![MyTrail Introduction](https://img.youtube.com/vi/plQ_3Ccr2Wc/0.jpg)](https://www.youtube.com/watch?v=plQ_3Ccr2Wc)

---

## SECTION 2 : EXECUTIVE SUMMARY / PAPER ABSTRACT
MyTrail is an application for exploring cities, recording leisurely walks or outdoor walking tracks. This application will generate routes based on some ideas proposed by users through intelligent reasoning and unique optimization models, and quickly display them in the built-in Google Maps. Users can then select any route created by the intelligent system and start exploring the surrounding area. Since each location is generated in real time through the Google API, MyTrail can avoid outdated locations. In addition, user route selection and feedback are also data for training the inference model, which means that more and more user data can make the model smarter.

Outdoor walking and running apps are widely adopted as health awareness grows. In places like Singapore—where dense urban fabric interleaves with parks and waterfronts—people frequently want novel, intent-aligned routes rather than static lists of attractions. Existing fitness apps focus on tracking and performance; lifestyle apps list venues but rarely transform free-form user intent into a closed-loop, non-crossing path.

There are many apps on the market that offer content for exploring the surrounding area, but there is a gap in the field of combining route planning and generating routes based on user input. In particular, there are very few apps that help users explore the surrounding environment and combine intelligent systems to assist in decision-making. Users need to simplify the process of exploring and starting outdoor activities.

* Lack of generative, exploration-oriented route creation.

- No intelligent ranking when multiple candidate routes exist.
- Systems rarely understand user intent; they force fixed patterns or manual filters.

MyTrail implements the workflow of user input-route generation, simplifies the user's operation complexity, and provides the function of converting user input into content that the system can understand, sorting and optimizing routes. Each time the user will get a different route, which may include parks, commercial areas, beaches, etc.

---

## SECTION 3 : CREDITS / PROJECT CONTRIBUTION

| Official Full Name  | Student ID (MTech Applicable)  | Work Items (Who Did What) | Email (Optional) |
| :------------ |:---------------:| :-----| :-----|
| Zheng Jiecheng | A0290838R | Team leader; NLU model training and deployment; 2-opt optimization implementation; Frontend development; | E1327869@u.nus.edu |
| Zhao Ziyang | A0285923U | Ranking_linear regression model training&deployment; backend server ranking_service | E1221735@u.nus.edu |
| Jin Ziping | A0263234L | Backend architecture& system design; Project technical scope; Development of Google map API service; System deployment design | E1010592@u.nus.edu |
| Zhao Yuan | A0263565W | Development of route generation module; Implementation of polar angle optimization algorithms; project documentation | E1010933@u.nus.edu |

---

## SECTION 4 : VIDEO OF SYSTEM MODELLING & USE CASE DEMO

[![MyTrail Technical Video](http://img.youtube.com/vi/QUgb5LyLT4E/0.jpg)](https://www.youtube.com/watch?v=QUgb5LyLT4E )

---

## SECTION 5 : USER GUIDE

`Refer to appendix <Appendix C_Installation and User Guide> in project report at Github Folder: ProjectReport`

### To run the system on local machine (Your Mac and iPhone)

1. **Overview**

   The repository is organized as:

   - frontend_app/ — Flutter mobile app (primary target: iOS)
   - backend/ — FastAPI server exposing REST endpoints.
   - models/nlu_model/ — NLU training code and a lightweight inference service

2. **Prerequisites**

   - **OS for iOS dev:** macOS 13+
   - **Xcode:** 18+ (with iOS Simulator); CocoaPods 1.13+ (sudo gem install cocoapods)
   - **Flutter SDK:** 3.x (Dart 3.x). Verify with flutter --version
   - **Python:** 3.11 with pip (recommend using virtualenv)
   - **Google Cloud keys**
     - Maps **SDK for iOS** (for the embedded map in Flutter)
     - **Places API** and **Directions API** keys (used by the backend)
   - **OpenAI API keys**
   - `$ git clone git@github.com:HowdyBunny/IRS-PM-2025-10-26-AIS07FT-GRP5-MyTrail.git`

3. **API KEYs and Address Modification**

   * iOS Maps SDK key: path: `ios/Runner/Info.plist`, find the `<key>GMSApiKey</key>` and modify
   * Backend API keys：path: `app/config/config.py`, find and modify `google_maps_api_key,` `openai_api_key`, `openai_base_url`, `openai_model`,`mongo_db`(optinal)
   * Model address: `nlu_basic_model_url`, `mongo_uri`

4. **Backend Setup (FastAPI)**

   Enter the backend folder and enter the terminal, enter the command：(create your python env first):

   `pip install -r requirements.txt`

   `python -m uvicorn app.main:app --host 192.168.0.207 --port 8000 --reload`

5. **NLU: Train and Serve（Flask）**

   For train:

   `cd models/nlu_model`

   `pip install -r requirements.txt`

   `python train.py`

   For deployment:

   `python app.py --host 0.0.0.0 --port 4000`

6. **Frontend App**

   `cd frontend_app`

   `flutter pub get`

   `flutter run`

   **If running on a physical device:**

   > Open ios/Runner.xcworkspace in Xcode.

   > Set a unique **Bundle Identifier** and your **Apple Team** (signing)

   > Build & run on your device.

7. **Run Order (Dev)**

   > **Start NLU** service (models/nlu_model/app.py on port 9000).

   > **Start Backend** (uvicorn on port 8000), with NLU_BASE_URL pointing to #1.

   > **Run Frontend** (flutter run) with backendBaseUrl pointing to #2.

---
## SECTION 6 : PROJECT REPORT / PAPER

`Refer to project report at Github Folder: ProjectReport`

**Recommended Sections for Project Report / Paper:**
- Introduction
- Business Case
- System Design
- Finding and Discussion
- Future Work
- Conclussion
- Appendix A: Project Proposal
- Appendix B: Mapped System Functionalities against knowledge, techniques and skills of modular courses: MR, RS, CGS
- Appendix C: Installation and User Guide

---
## SECTION 7 : MISCELLANEOUS

`Refer to Github Folder: Miscellaneous`

Model Training Data
