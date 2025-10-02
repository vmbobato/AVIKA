# Flask Web Application 🚀

This repository contains a **Flask-based web application** deployed on **AWS Elastic Beanstalk**.  
It is a simple starting point for building and deploying Python web apps to the cloud.

---

## 📦 Features
- Flask web server with customizable routes
- AWS Elastic Beanstalk deployment support
- `.gitignore` configured to exclude caches, local configs, and environment files
- Easily extensible for databases, APIs, and frontend integration

---

## 🛠️ Requirements
- Python 3.8+  
- Flask  
- AWS Elastic Beanstalk CLI (`eb`)  
- Git  

Install dependencies:
```bash
pip install -r requirements.txt
```

---

## 🚀 Running Locally
1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/your-repo.git
   cd your-repo
   ```

2. Start the Flask app:
   ```bash
   python application.py
   ```
   The app will be available at: [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## ☁️ Deployment to AWS Elastic Beanstalk
1. Initialize Elastic Beanstalk:
   ```bash
   eb init -p python-3.8 flask-app --region us-east-1
   ```

2. Create the environment:
   ```bash
   eb create flask-env
   ```

3. Open the deployed app:
   ```bash
   eb open
   ```

---

## 📂 Project Structure
```
.
├── application.py      # Main Flask app
├── requirements.txt    # Python dependencies
├── .gitignore          # Ignored files (pycache, configs, etc.)
└── README.md           # Project documentation
```

---

## 📝 Notes
- Update `requirements.txt` whenever you add new Python packages:
  ```bash
  pip freeze > requirements.txt
  ```
- Do **not** push `.elasticbeanstalk/`, `.avika/`, or `__pycache__/` — these are ignored automatically.

---

## 📄 License
This project is open source and available under the [MIT License](LICENSE).
