## setup UI
 * cd frontend/ui
 * create the env.local file (see below)
 * you may need to install npm
 * you may need to do **npm install vue-cli-service**
 * Then **npm run build**
 * **npm run serve**


### The .env.local file
```python
NODE_ENV=development
PORT=8080

VUE_APP_SKIP_AUTH=true
VUE_APP_REMOTE=false

VUE_APP_ID_TOKEN=ABCD
```

### Point to API GW

 * CORS should be enabled for API GW. If not chrome has an extension to allow it
 * change poolId and clientId in aws-exports.json
 * set VUE_APP_REMOTE to true in .env.local
 * change the following line so that if VUE_APP_REMOTE is true then use the API GW endpoint
```javascript
const BASE_URLS = {
  trials: process.env.VUE_APP_REMOTE === 'true' ? 'https://205iwh3n9g.execute-api.us-east-1.amazonaws.com/prod/api/v1/' : '/api/v1/',  // Only for developer's laptop, this full-URL applies.  Deployment only uses relative URL.
  //trials: 'api/v1/'
};
```
**.env.local**
```javascript
VUE_APP_REMOTE=true
```
 **aws-exports.json**
```javascript
if ( window.location.host == "localhost:8080" ) {             // Front-end Developer's Laptop
    poolId = 'us-east-1_Sx8vl4NET';
    clientId = '6h5kc0j5ar7rrba037vr0k82lp';
    domainSuffixCognito = "dev"
```
### Start the UI server
 * **npm run serve**


## The backend server

 * go to api/scripts dir in backend repo
 * edit the server.py if needed
 * PORT should already be 3002 but you can change it depending on what UI server wants
 * run server.py
 * You should see the following

```python
serving at port 3002
```

## Some info on the backend
 * server.py uses fact.sam.yml
 * it loads the necessary lambda handlers in dynamically based on that file
 * but it still needs explicit imports like below
```python
import get_filtering_criteria
import handler
import EvalDynamicExpression
import constants
import delete_criteria_type
import delete_search_sessions
import delete_trial_criteria
...
```
 * Occasionally PyCharm will get confused and inexplicably erase those explict imports
