# EAROS Auth Testing Playbook (Emergent Google Auth)

## Step 1 — Create Test User & Session
```bash
mongosh --eval "
use('test_database');
var userId = 'test-user-' + Date.now();
var sessionToken = 'test_session_' + Date.now();
db.users.insertOne({
  user_id: userId,
  email: 'test.recruiter.' + Date.now() + '@levelshift.ai',
  name: 'Test Recruiter',
  picture: 'https://via.placeholder.com/150',
  role: 'recruiter',
  organization_id: 'org_levelshift',
  created_at: new Date()
});
db.user_sessions.insertOne({
  user_id: userId,
  session_token: sessionToken,
  expires_at: new Date(Date.now() + 7*24*60*60*1000),
  created_at: new Date()
});
print('Session token: ' + sessionToken);
print('User ID: ' + userId);
"
```

## Step 2 — Test Backend
```bash
curl -X GET "$REACT_APP_BACKEND_URL/api/auth/me" \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN"

curl -X GET "$REACT_APP_BACKEND_URL/api/world/jobs" \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN"
```

## Step 3 — Browser Testing (Playwright)
```python
await page.context.add_cookies([{
    "name": "session_token",
    "value": "YOUR_SESSION_TOKEN",
    "domain": "hiring-runtime.preview.emergentagent.com",
    "path": "/",
    "httpOnly": True,
    "secure": True,
    "sameSite": "None"
}])
await page.goto("https://hiring-runtime.preview.emergentagent.com/dashboard")
```

## Success Indicators
- `/api/auth/me` returns user object (user_id, email, name, role, organization_id)
- Dashboard loads without redirect to /login
- All EAROS pages load with authenticated data
