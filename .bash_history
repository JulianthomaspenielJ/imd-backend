ls
rm finalcompliance.py 
nano finalcompliance.py
python3 finalcompliance.py
rm finalcompliance.py
nano finalcompliance.py
python3 finalcompliance.py
nano finalcompliance.py
rm finalcompliance.py
ls
cat compliance.py
ls
nano finalcompliance.py
python3 finalcompliance.py
ls
rm finalcompliance.py
nano finalcompliance.py
python3 finalcompliance.py
ls
nano costcompliance.py
python3 costcompliance.py
ls
cat costcompliance.py
ls
rm costcompliance.py
nano costcompliance.py
python3 costcompliance.py
ls
rm compliance.py 
rm finalcompliance.py 
cat costcompliance.py
ls
cat costcompliance.py 
ls
compliance.py
nano compliance.py
python3 compliance.py
ls
su postgres
ls
cat v5finalcode.py
ls
v7finalcode.py
nano v7finalcode.py
python3 v7finalcode.py
ls
rm v7finalcode.py 
sudo su
sudo su
ls
nano v7finalcode.py
ls
nano v7finalcode.py
su postgres
ls
python3 v7finalcode.py
su postgres
ls
cat v7finalcode.py 
nano v8finalcode.py
python3 v8finalcode.py
ls
su postgres
su postgres
sudo su
ls
nano service_status.py
python3 service_status.py
rm service_status.py 
nano serviceStatus.py
python3 serviceStatus.py
rm serviceStatus.py 
ls
nano forecast.py
python3 forecast.py
rm forecast.py 
nano forecast.py
python3 forecast.py
nano forecast.py
python3 forecast.py
su postgres
ls
rm forecast.py 
nano forecast.py
python3 forecast.py
su postgres
nano forecastapi.py
uvicorn forecastapi:app --host 0.0.0.0 --port 8000
lsof -i :8000
uvicorn forecastapi:app --host 0.0.0.0 --port 8000
sudo lsof -i:8000
kill -9 166981
sudo kill -9 166981

sudo lsof -i:8000
uvicorn forecastapi:app --host 0.0.0.0 --port 8000
ls
cat forecastapi.py 
ls
cat finalcostapi.py 
ls
cat taxsupportapi.py
ls
cat finalcostapi.py
ls
cat costapi.py
ls
rm finalcostapi.py 
nano taxsupportapi.py 
cat costapi.py 
ls
cat forecastapi.py
ls
rm forecastapi.py 
nano forecastapi.py
python3 forecastapi.py 
uvicorn forecastapi:app --host 0.0.0.0 --port 8000
cat forecastapi.py
ls
cat costapi.py 
ls
rm taxsupportapi.py 
ls
nano finalcostapi.py
ls
rm forecastapi.py 
ls
uvicorn finalcostapi:app --host 0.0.0.0 --port 8000
ls
cat tax_support.py 
ls
cat v7finalcode.py 
cat finalcostapi.py 
ls
cat forecast.py
ls
LS
ls
cat nano v8finalcode.py 
cat v8finalcode.py 
python3 v7finalcode.py 
su postgres
ls
python3 v8finalcode.py 
ls
su postgres
ls
rm v7finalcode.py 
cat v8finalcode.py
ls
cat v8finalcode.py 
ls
nano v8finalcodeapi.py
uvicorn v8finalcodeapi:app --host 0.0.0.0 --port 8000
ls
uvicorn finalcostapi:app --host 0.0.0.0 --port 8000
sudo su
sudo su
sudo su
ls
uvicorn v8finalcodeapi:app --host 0.0.0.0 --port 8003
cat v8finalcodeapi.py 
uvicorn v8finalcodeapi:app --host 0.0.0.0 --port 8003
ls
cat v8finalcodeapi.py 
ls
rm v8finalcodeapi.py
nano v8apicode.py
uvicorn v8apicode:app --host 0.0.0.0 --port 8003
ls
su postgres
ls
nano daily_cost.py
ls
python3 daily_cost.py 
ls
nano monthly_cost.py 
python3 monthly_cost.py
ls
nano tax_support.py 
python3 tax_support.py 
ls
nano forecast.py
python3 forecast.py 
ls
nano customdate.py
python3 customdate.py
ls
nano costcompliance.py
python3 costcompliance.py 
ls
uvicorn finalcostapi:app --host 0.0.0.0 --port 8003
uvicorn finalcostapi:app --host 0.0.0.0 --port 8000
lsof -i:8000
kill -9 174809
uvicorn finalcostapi:app --host 0.0.0.0 --port 8000
ls
nano v8finalcode.py 
cat v8apicode.py 
ls
rm v8apicode.py 
nano apiv8.py
uvicorn apiv8:app --host 0.0.0.0 --port 8000
uvicorn apiv8:app --host 0.0.0.0 --port 8003
ls
rm apiv8.py 
nano v8api.py
uvicorn v8api:app --host 0.0.0.0 --port 8003
ls
uvicorn finalcostapi:app --host 0.0.0.0 --port 8000
sudo su 
sudo su
sudo su
uvicorn v8api:app --host 0.0.0.0 --port 8003
ls
su postgres
ls
python3 costcompliance.py 
python3 forecast.py 
python3 monthly_cost.py 
python3 daily_cost
ls
python3 daily_cost.py
ls
python3 customdate.py
python3 tax_support.py 
cat costapi.py
uvicorn finalcostapi:app --host 0.0.0.0 --port 8000
nano month_current.py
rm month_current.py 
nano fetch_and_store_monthly_cost.py
apimonthlycurrent.py
nano apimonthlycurrent.py
python3 fetch_and_store_monthly_cost.py 
uvicorn apimonthlycurrent:app --host 0.0.0.0 --port 8000
uvicorn apimonthlycurrent:app --host 0.0.0.0 --port 8004
LS
ls
cat fetch_and_store_monthly_cost.py 
ls
cat apimonthlycurrent.py 
ls
rm fetch_and_store_monthly_cost.py 
nano monthly_current
nano apimonthlyservice current.py
su postgres
ls
rm apimonthlycurrent.py 
rm apimonthlyservice 
rm monthly_current
ls
nano monthly_current
python3 monthly_current
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
# ---------- DB Config ----------
DB_CONFIG = {
}
app = FastAPI()
# ---------- CORS Middleware ----------
app.add_middleware(
)
# ---------- API: Get Monthly Costs + Service Breakdown ----------
@app.get("/monthly-current")
def get_monthly_current():
nano apimonthly_current.py
uvicorn apimonthly:app --host 0.0.0.0 --port 8004
uvicorn apimonthly_current:app --host 0.0.0.0 --port 8004
ls
rm apimonthly_current.py
rm monthly_current 
ls
rm current.py
nano monthlycurrent.py
python3 monthlycurrent.py
nano monthlycurrentapi.py
ls
uvicorn monthlycurrentapi:app --host 0.0.0.0 --port 8004
uvicorn v8api:app --host 0.0.0.0 --port 8003
uvicorn apimonthlycurrent:app --host 0.0.0.0 --port 8000
uvicorn finalcostapi:app --host 0.0.0.0 --port 8000
sudo su
ls
cat forecast.py
ls
nano service_status
nano service_status_api.py
python3 service_status
nano service_status
python3 service_status
ls
rm service_status
nano service_status
nano service_status.py
ls
rm service_status_api.py
nano servicestatusapi.py
ls
python3 service_status.py 
ls
rm service_status.py 
nano service_status.py
python3 service_status.py
su postgres
ls
rm service_status.py 
nano service_status.py
python3 service_status.py
nano service_status.py
rm service_status.py 
nano service_status.py
python3 service_status.py 
su postgres
ls
rm service_status.py
nano service_status.py
python3 service_status.py 
ls
rm service_status.py 
rm servicestatusapi.py 
nano service_status.py
python3 service_status.py 
nano service_status.py
python3 service_status.py 
nano service_status.py
rm service_status.py 
nano service_status.py
python3 service_status.py
rm service_status.py 
nano service_status.py
ls
rm service_status.py
nano service_status.py
ls
nano costcompliance.py 
nano servicestatus.py
ls
nano servicestatus.py
sudo su
ls
vi servicestatus.py
nano servicestatus.py 
python3 servicestatus.py 
su postgres
ls
rm servicestatus.py 
ls
nano service_status.py
ls
python3 service_status.py
su postgres
ls
nano servicestatusfinal.py
python3 servicestatusfinal.py
rm servicestatusfinal.py 
nano servicestatusfinal.py
python3 servicestatusfinal.py 
su postgres
ls
rm servicestatusfinal.py 
nano servicestatusfinal.py 
python3 servicestatusfinal.py 
rm servicestatusfinal.py 
nano servicestatusfinal.py
python3 servicestatusfinal.py 
rm servicestatusfinal.py 
nano servicestatusfinal.py
python3 servicestatusfinal.py 
nano servicestatusfinal.py
rm servicestatusfinal.py 
nano servicestatusfinal.py
su postgres
ls
rm servicestatusfinal.py 
rm service_status.py 
nano service_status.py
python3 service_status.py
su postgres
ls
rm service_status.py 
nano service_status.py
python3 service_status.py 
ls
nano service_status_api.py
ls

uvicorn finalcostapi:app --reload --host 0.0.0.0 --port 8000
ls
uvicorn service_status_api:app --reload --host 0.0.0.0 --port 8003
mkdir savings
cd savings
mkdir orphaned
ls
cd orphaned
ls
uvicorn monthlycurrentapi:app --reload --host 0.0.0.0 --port 8000
uvicorn monthlycurrentapi:app --reload --host 0.0.0.0 --port 8004
ls
rm service_status.py 
nano service_status.py
python3 service_status.py
ls
rm service_status.py 
su postgres
ls
nano service_status.py
python3 service_status.py
su postgres
cat service_status.py
ls
rm service_status.py 
ls
nano service_status.py
python3 service_status.py 
ls
rm service_status.py 
ls
su postgres
ls
cat monthly_cost.py
ls
su postgres
ls
nano serviceStatus.py
python3 serviceStatus.py
ls
su postgres
rm serviceStatus.py 
nano serviceStatus.py
python3 serviceStatus.py
su postgres
ls
uvicorn service_status_api:app --reload --host 0.0.0.0 --port 8003
nano service_status_api.py
ls
nano daily_cost.py
ls
nano v5finalcode.py
python3 v5finalcode.py
cat v5finalcode.py
cat v6finalcode.py 
ls
nano v5finalcode.py
su postgres
nano v5finalcode.py
python3 v5finalcode.py
nano v5finalcode.py
python3 v5finalcode.py
nano v5finalcode.py
nano curfinalcode.py
su postgres
python3 curfinalcode.py
su postgres
ls
rm curfinalcode.py 
nano curfinalcode.py
python3 curfinalcode.py
ls
nano v9finalcode.py
ls
python3 curfinalcode.py 
ls
cat curfinalcode.py 
ls
rm v5finalcode.py.save
rm v2finalcost.py 
rm v3finalcode.py 
rm v4finalcode.py 
ls
python3 v8finalcode.py 
nano v8finalcode.py 
ls
su postgred
su postgres
ls
cat curfinalcode.py 
ls
updatedcurfinalcode.py
nano updatedcurfinalcode.py
python3 updatedcurfinalcode.py
su postgres
ls
python3 updatedcurfinalcode.py 
su postgres
nano apicur.py
uvicorn apicur:app --reload --host 0.0.0.0 --port 8000
rm apicur.py 
nano apicur.py
uvicorn apicur:app --reload --host 0.0.0.0 --port 8000
ls
rm v6finalcode.py 
rm v8finalcode.py 
rm v8api.py 
ls
nano apicategory.py
uvicorn apicategory:app --reload
rm apicategory.py 
nano category_costs.py
python3 category_costs.py
nano category_costs.py
python3 category_costs.py
su postgres
python3 updatedcurfinalcode.py 
ls
rm category_costs.py
nano category_costs.py
python3 category_costs.py
nano category_costs.py
python3 category_costs.py
la
ls
rm category_costs.py
nano category_costs.py
python3 category_costs.py
rm category_costs.py
nano category_costs.py
python3 category_costs.py
nano category_costs.py
python3 category_costs.py
nano category_costs.py
python3 category_costs.py
nano category_costs.py
python3 category_costs.py
ls
rm curfinalcode.py 
nano updatedcurfinalcode.py 
cat updatedcurfinalcode.py 
su postgres
ls
nano multipleusercur.py
python3 multipleusercur.py
ls
cat multipleusercur.py 
nano ri_savingsplan.py
python3 ri_savingsplan.py
nano ri_savingsplan.py
python3 ri_savingsplan.py
rm ri_savingsplan.py 
nano ri_savingsplan.py
python3 ri_savingsplan.py
rm ri_savingsplan.py 
nano ri_savingsplan.py
python3 ri_savingsplan.py
su postgres
su postgres
ls
cat multipleusercur.py 
ls
nano updmultipleusercur.py
python3 updmultipleusercur.py
ls
cat category_costs.py
nano category_costs.py
cat category_costs.py 
ls
rm multipleusercur.py 
nano updcategorycost.py
python3 updcategorycost.py
cat updmultipleusercur.py 
ls
cat updatedcurfinalcode.py 
ls
cat updcategorycost.py 
ls
rm compliance.py 
ls
rm final_cost.py 
ls
rm v5finalcode.py 
rm v5finalcodeapi.py 
ls
python3 updmultipleusercur.py 
su postgres
ls
cat updmultipleusercur.py 
ls
nano updapimultipleusercur.py
uvicorn updapimultipleusercur.py:app --reload --host 0.0.0.0 --port 8000
uvicorn updapimultipleusercur:app --reload --host 0.0.0.0 --port 8000
sudo su
ls
rm apicur.py 
ls
nano costapi.py 
nano finalcostapi.py 
rm costapi.py 
cat finalcostapi.py 
ls
cat monthlycurrentapi.py 
ls
cat updapimultipleusercur.py 
ls
cat category_costs.py 
ls
rm category_costs.py 
cat updcategorycost.py 
ls
nano apiupdcost_category.py
uvicorn apiupdcost_category:app --reload --host 0.0.0.0 --port 8000
uvicorn apiupdcost_category:app --reload --host 0.0.0.0 --port 8001
uvicorn apiupdcost_category:app --reload --host 0.0.0.0 --port 8004
ls
cat apiupdcost_category.py 
ls
cat updapimultipleusercur.py 
ls
cat monthlycurrentapi.py 
ls
cat apiupdcost_category.py cat service_status_api.py 
cat service_status_api.py 
ls
cat service_status_api.py 
sudo su
ls
sudo su
nano completeapi.py
uvicorn completeapi:app  --reload --host 0.0.0.0 --port 8003
sudo su
ls
cat finalcostapi.py
sudo su
sudo su
ls
rm completeapi.py 
nano completeapi.py 
uvicorn completeapi:app --reload --host 0.0.0.0 --port 8003
lsof -i:8003
kill -9 223411
kill -9 223814
uvicorn completeapi:app --reload --host 0.0.0.0 --port 8003
su postgres
ls
rm completeapi.py 
nano completeapi.py 
uvicorn completeapi:app --reload --host 0.0.0.0 --port 8003
nano completeapi.py 
uvicorn completeapi:app --reload --host 0.0.0.0 --port 8003
rm completeapi.py 
ls
uvicorn completeapi:app --reload --host 0.0.0.0 --port 8003
rm completeapi.py
ls
uvicorn finalcostapi:app --reload --host 0.0.0.0 --port 8003
uvicorn apiupdcost_category:app --reload --host 0.0.0.0 --port 8000
ls
uvicorn updapimultipleusercur:app --reload --host 0.0.0.0 --port 8000
sudo su
sudo su
ls
cat finalcostapi.py 
ls
cat apiupdcost_category.py 
ls
cat updapimultipleusercur.py 
ls
cat service_status_api.py 
ls
sudo su
clear
sudo su
curl ifconfig.me
la
ls
nano deepdive.py
ll
sudo su
sudo su
ls
su postgres
nano instancedeepdive.py
python3 instancedeepdive.py 
rm instancedeepdive.py 
nano instancedeepdive.py
python3 instancedeepdive.py 
su postgres
ls
nano instancedeepdive.py 
su postgres
ls
nano updmultipleusercur.py
rm deepdive.py.save 
rm instancedeepdive.py 
nano instancedeepdive.py 
ls
su postgres
ls
nano ec2deepdive.py
python3 ec2deepdive.py
nano ec2deepdive.py
ls
rm ec2deepdive.py 
nano ec2deepdive.py
ls
su postgres
ls
nano instancedeepdive.py 
rm instancedeepdive.py 
nano ec2deepdive.py
python3 ec2deepdive.py
rm ec2deepdive.py 
nano ec2deepdive.py
python3 ec2deepdive.py
su postgres
ls
rm ec2deepdive.py 
nano ec2deepdive.py
python3 ec2deepdive.py
nano ec2deepdive.py
su postgres
ls
rm ec2deepdive.py 
nano ec2deepdive.py
python3 ec2deepdive.py
rm ec2deepdive.py 
nano ec2deepdive.py
rm ec2deepdive.py 
nano ec2deepdive.py
python3 ec2deepdive.py 
su postgres
rm ec2deepdive.py 
nano ec2deepdive.py
python3 ec2deepdive.py 
su postgres
ls
rm ec2deepdive.py 
nano ec2deepdive.py
python3 ec2deepdive.py 
nano ec2deepdive.py
python3 ec2deepdive.py 
ls
su postgres
ls
nano ec2_autostartstop.py
python3 ec2_autostartstop.py
nano ec2_autostartstop.py
python3 ec2_autostartstop.py
su postgres
su postgres
sudo su
sudo su
rm ec2deepdive.py 
nano ec2deepdive.py
python3 ec2deepdive.py 
su postgres
ls
rm ec2deepdive.py 
nano instancemetrics.py
python3 instancemetrics.py
ls
nano ec2-metrics.py
python3 ec2-metrics.py
su postgres
rm ec2-metrics.py 
ls
python3 updmultipleusercur.py 
nano updmultipleusercur.py 
ls
su postgres
su postgres
ls
nano ec2cost_metrics.py
python3 ec2cost_metrics.py
su postgres
ls
cat ec2cost_metrics.py 
su postgres
ls
su postgres
ls
rm instancemetrics.py 
cat ec2cost_metrics.py 
su postgres
ls
nano updec2cost_metrics.py
python3 updec2cost_metrics.py
nano updec2cost_metrics.py
ls
nano updec2_cost_metrics.py
python3 updec2_cost_metrics.py
su postgres
python3 updec2_cost_metrics.py
ls
cat updec2cost_metrics.py 
rm updec2cost_metrics.py 
ls
cat updec2_cost_metrics.py 
ls
nano costcompliance.py 
python3 costcompliance.py 
ls
su postgres
ls
sudo su
ls
rm ec2_autostartstop.py 
nano ec2_autostartstop.py
python3 ec2_autostartstop.py
nano ec2_autostartstop.py
su postgres
nano ec2_autostartstop.py
python3 ec2_autostartstop.py
su postgres
cat ec2_autostartstop.py 
ls
nano ec2startstop_api.py
uvicorn ec2startstop_api:app -- reload 
uvicorn ec2startstop_api:app  --reload --host 0.0.0.0 --port 8003
ls
cat costcompliance.py 
ls
nano apicostcompliance.py
uvicorn apicostcompliance:app  --reload --host 0.0.0.0 --port 8003
ls
cat updec2_cost_metrics.py 
ls
nano apiec2_cost_metrics.py
python3 apiec2_cost_metrics.py
uvicorn apiec2_cost_metrics:app  --reload --host 0.0.0.0 --port 8003
sudo su
sudo su
sudo su
ls
select * from monthlycurrent.py ;
su postgres
nano completeapi.py
uvicorn completeapi:app --reload --8000
uvicorn completeapi:app --reload --port 8000
uvicorn completeapi:app  --reload --host 0.0.0.0 --port 8003
nano completeapi.py
uvicorn completeapi:app  --reload --host 0.0.0.0 --port 8003
ls
cat completeapi.py 
clear
cat completeapi.py 
ls
sudo su
ls
nano singleendpointapi.py
uvicorn singleendpointapi:app  --reload --host 0.0.0.0 --port 8003
uvicorn singleendpointapi:app  --reload --host 0.0.0.0 --port 8000
ls
uvicorn completeapi:app  --reload --host 0.0.0.0 --port 8004
sudo su 
sudo su
sudo su
ls
python3 daily_cost.py 
python3 forecast.py 
python3 monthlycurrent.py
ls
python3 daily_cost.py 
cat monthlycurrent.py
ls
nano updmonthlycurrent.py
python3 updmonthlycurrent.py
nano updmonthlycurrent.py
ls
python3 forecast.py 
python3 daily_cost.py 
cat daily_cost.py 
ls
nano upddaily_cost.py
python3 upddaily_cost.py
rm upddaily_cost.py 
nano updaily_cost.py
python3 updaily_cost.py
nano updaily_cost.py
python3 updaily_cost.py
su postgres
ls
mkdir Dashboard
cd das
cd Dashboard/
ls
touch currentMonthCostAPI.py
nano currentMonthCostAPI.py
ls
uvicorn currentMonthCostAPI:app  --reload --host 0.0.0.0 --port 8000
nano currentMonthCostAPI.py
uvicorn currentMonthCostAPI:app  --reload --host 0.0.0.0 --port 8000
ls
nano currentmonth+forecastapi.py
uvicorn currentmonth+forecastapi:app  --reload --host 0.0.0.0 --port 8000
ls
nano cm+fm+serbreakapi.py
ls
uvicorn cm+fm+serbreakapi:app  --reload --host 0.0.0.0 --port 8000
ls
nano finalcm+fm+serbreakapi.py
uvicorn finalcm+fm+serbreakapi:app  --reload --host 0.0.0.0 --port 8000
rm finalcm+fm+serbreakapi.py 
uvicorn cm+fm+serbreakapi:app  --reload --host 0.0.0.0 --port 8000
ls
rm cm+fm+serbreakapi.py 

uvicorn cm+fm+serbreakapi:app  --reload --host 0.0.0.0 --port 8000
ls
nano dailycostapi.py
uvicorn dailycostapi:app  --reload --host 0.0.0.0 --port 8000
ls
cat cm+fm+serbreakapi.py 
sudo su
sudo su
sudo su
ls
cd dashboard
cd Dashboard
ls
cd Dashboard
ls
nano cm+fm+sb+dcapi.py
su postgres
cd Dashboard/
ls
rm cm+fm_sb+dcapi.py.save
ls
rm cm+fm+sb+dcapi.py.save
nano cm+fm+sb+dcapi.py
ls
cat cm+fm+serbreakapi.py
ls
cat dailycostapi.py 
nano cm+fm+sb+dcapi.py
uvicorn cm+fm+sb+dcapi:app  --reload --host 0.0.0.0 --port 8000
ls
Top5api.py
nano Top5api.py
uvicorn Top5api:app  --reload --host 0.0.0.0 --port 8000
ls
rm top5api.py
rm Top5api.py
nano Top5api.py
uvicorn Top5api:app  --reload --host 0.0.0.0 --port 8000
ls
rm Top5api.py 
nano Top5api.py
uvicorn Top5api:app  --reload --host 0.0.0.0 --port 8000
ls
cat cm+fm+sb+dcapi.py 
ls
nano cm+fm+sb+dc+top5api.py
uvicorn cm+fm+sb+dc+top5api:app  --reload --host 0.0.0.0 --port 8000
sudo su
sudo su
sudo su
sudo su
ls
cd Dashboard/
ls
cat cm+fm+sb+dc+top5api.py
cd Dashboard/
ls
cat cm+fm+db+dc+top5api.py
cat cm+fm+sb+dc+top5api.py
ls
nano cm+fm+sb+dc+top5api.py
uvicorn cm+fm+sb+dc+top5api:app  --reload --host 0.0.0.0 --port 8000
nano cm+fm+sb+dc+top5api.py
uvicorn cm+fm+sb+dc+top5api:app  --reload --host 0.0.0.0 --port 8000
nano cm+fm+sb+dc+top5api.py
cd ..
ls
llllllllllllllllllllllllllllllllllllllllllllllllllllllllll
ll
uvicorn apiec2_cost_metrics:app  --reload --host 0.0.0.0 --port 8000
uvicorn apiec2_cost_metrics:app  --reload --host 0.0.0.0 --port 8001
uvicorn apiec2_cost_metrics:app  --reload --host 0.0.0.0 --port 8002
ls
cat apiec2_cost_metrics.py 
uvicorn apiec2_cost_metrics:app  --reload --host 0.0.0.0 --port 8002
ls
cat updec2_cost_metrics.py 
nano deepdive.py
python3 deepdive.py
su postgres
python3 deepdive.py
su postgres
ls
rm apiec2_cost_metrics.py 
rm updec2_cost_metrics.py 
rm ec2cost_metrics.py 
ls
cat deepdive.py 
apideepdive.py
nano apideepdive.py
uvicorn apideepdive:app  --reload --host 0.0.0.0 --port 8002
cd Dashboard/
ls
cd Dashboard/
ls
uvicorn cm+fm+sb+dc+top5api:app  --reload --host 0.0.0.0 --port 8002
uvicorn cm+fm+sb+dc+top5api:app  --reload --host 0.0.0.0 --port 8000
sudo su
uvicorn apideepdive:app  --reload --host 0.0.0.0 --port 8002
cd Dashboard/
uvicorn cm+fm+sb+dc+top5api:app  --reload --host 0.0.0.0 --port 8000
ls
uvicorn apideepdive:app  --reload --host 0.0.0.0 --port 8002
ls
cd Dashboard/
ls
uvicorn cm+fm+sb+dc+top5api:app  --reload --host 0.0.0.0 --port 8000
sudo su
ls
cd savings/
ls
cd orphaned/
ls
cd Dashboard/
uvicorn cm+fm+sb+dc+top5api:app  --reload --host 0.0.0.0 --port 8000
uvicorn apideepdive:app  --reload --host 0.0.0.0 --port 8002
sudo su
sudo su
sudo su
ls
cd savings/
ls
cd orphaned/
ls
sudo su
ls
cd Dashboard/
uvicorn cm+fm+sb+dc+top5api:app  --reload --host 0.0.0.0 --port 8000
ls
cd savings/
ls
cd orphaned/
ls
su postgres
ls
nano orphanedvolume.py
su postgres
uvicorn apideepdive:app  --reload --host 0.0.0.0 --port 8002
sudo su
cd Dashboard/
uvicorn cm+fm+sb+dc+top5api:app  --reload --host 0.0.0.0 --port 8000
ls
cd savings/
ls
cd orphaned/
ls
nano orphanedvolume.py 
python3 orphanedvolume.py 
su postgres
ls
truncate orphanedvolume.py 
rm orphanedvolume.py 
nano orphanedvolume.py
python3 orphanedvolume.py 
su postgres
python3 orphanedvolume.py 
ls
su postgres
ls
cat orphanedvolume.py 
python3 orphanedvolume.py 
su postgres
cd ..
ls
cd /
cd /ims/business_continuity/
ls
cd ..
ls
cd observability/
ls
cat elastic_ip
cat elastic_ip.py
cd elastic_ip/
ls
cat v1.py 
cd ..
ls
cd /home/
ls
cd ubuntu
ls
cd savings
ls
cd orphaned/
ls
nano orphanedeip.py
python3 orphanedeip.py
nano orphanedeip.py
rm orphanedeip.py 
ls
rm orphanedvolume.py 
sudo su
sudo su
uvicorn apideepdive:app  --reload --host 0.0.0.0 --port 8002
uvicorn cm+fm+sb+dc+top5api:app  --reload --host 0.0.0.0 --port 8000
cd Dashboard/
uvicorn cm+fm+sb+dc+top5api:app  --reload --host 0.0.0.0 --port 80004
uvicorn cm+fm+sb+dc+top5api:app  --reload --host 0.0.0.0 --port 8000
sudo su
sudo su
sudo su
sudo su
cd Dashboard/
uvicorn cm+fm+sb+dc+top5api:app  --reload --host 0.0.0.0 --port 8000
uvicorn apideepdive:app  --reload --host 0.0.0.0 --port 8002
sudo su
ls
cd Dashboard/
uvicorn cm+fm+sb+dc+top5api:app  --reload --host 0.0.0.0 --port 8000
ls
cd savings
ls
cd orphaned
ls
python3 orphaneddisk.py 
python3 orphanedreip.py
python3 orphanedeip.py
su postgres
cd ..
ls
python3 updmultipleusercur.py 
cd savings/
ls
cd orphaned/
ls
python3 orphanedeip.py 
python3 orphaneddisk.py 
su postgres
cd ..
ls
python3 daily_cost.py 
python3 monthly_cost.py 
ls
python3 monthlycurrent.py
python3 forecast.py 
ls
python3 updmultipleusercur.py 
ls
python3 updaily_cost.py 
ls
python3 updmonthlycurrent.py 
cd savings/
cd orphaned/
ls
su postgres
ls
nano orphanedsnapshots.py
python3 orphanedsnapshots.py
ls
su postgres
python3 orphanedsnapshots.py
su postgres
python3 orphanedsnapshots.py
ls
su postgres
python3 orphanedsnapshots.py
su postgres
nano orphanedsnapshots.py
su postgres
cd ..
ls
python3 updmultipleusercur.py 
cd savings
ls
cd orphaned/
ls
python3 orphaneddisk.py 
python3 orphanedeip.py 
ls
python3 orphanedsnapshots.py 
su postgres
uvicorn apideepdive:app  --reload --host 0.0.0.0 --port 8002
ls
cd savings/orphaned/
ls
nano orphanedsnapshots.py 
python3 orphanedsnapshots.py 
su postgres
LS
ls
cat orphanedsnapshots.py 
ls
rm orphanedsnapshots.py 
nano orphanedsnapshots.py
python3 orphanedsnapshots.py 
su postgres
ls
sudo su 
sudo su
sudo lsof -i :8012
sudo su
cd savings
cd orphaned
ls
su postgres
sudo su
cd Dashboard/
ls
uvicorn cm+fm+sb+dc+top5api:app  --reload --host 0.0.0.0 --port 8002
lsof -i:8000
uvicorn cm+fm+sb+dc+top5api:app  --reload --host 0.0.0.0 --port 8002
uvicorn cm+fm+sb+dc+top5api:app  --reload --host 0.0.0.0 --port 8000
ls
cd savings/
cd orphaned/
ls
su postgres
ls
nano underutilized.py
python3 underutilized.py
su postgres
ls
nano updunderutilized.py
python3 updunderutilized.py
su postgres
la
cat orphaneddisk.py 
ls
rm orphaneddisk.py 
nano orphaneddisk.py
python3 orphaneddisk.py
ls
rm orphaneddisk.py 
nano orphaneddisk.py
python3 orphaneddisk.py
ls
rm orphaneddisk.py 
nano orphaneddisk.py
python3 orphaneddisk.py
nano orphaneddisk.py
python3 orphaneddisk.py
rm orphaneddisk.py 
nano orphaneddisk.py
python3 orphaneddisk.py 
nano orphaneddisk.py 
cat orphaneddisk.py 
ls
nano neworphaneddisk.py
python3 neworphaneddisk.py 
su postgres
ls
rm neworphaneddisk.py 
nano neworphaneddisk.py
python3 neworphaneddisk.py
su postgres
ls
nano blahtest.py
python3 blahtest.py 
rm blahtest.py 
nano blahtest.py
python3 blahtest.py 
rm blahtest.py 
nano blahtest.py
python3 blahtest.py 
su postgres
cd savings/orphaned/
l
ls
cat finalorphanedisk.py 
ls
cat orphanedeip.py 
ls
cat orphanedsnapshots.py 
ls
cat updunderutilized.py 
ls
finalapi.py
nano finalapi.py
uvicorn finalapi:app --reload --host 0.0.0.0 --port 8000
cd ..
node -v
sudo apt update
sudo apt install -y nodejs npm
sudo npm install -g pm2
ls
cd Dashboard/
ls
pm2 start "uvicorn cm+fm+sb+dc+top5api:app --host 0.0.0.0 --port 8000" --name dashboard-api --interpreter python3
pm2 stop "uvicorn cm+fm+sb+dc+top5api:app --host 0.0.0.0 --port 8000" --name dashboard-api --interpreter python3
pm2 stop dashboard-api
pm2 delete dashboard-api
pm2 start uvicorn --name dashboard-api --interpreter python3 --   cm+fm+sb+dc+top5api:app --host 0.0.0.0 --port 8000
ls
cd ..
ls
pm2 start uvicorn --name deepdiveApi --interpreter python3 --   apideepdive:app --host 0.0.0.0 --port 8002
cd savings
cd orphaned
ls
pm2 start uvicorn --name savings-api --interpreter python3 --   finalapi:app --host 0.0.0.0 --port 8001
pm2 stop 342624
uvicorn finalapi:app --reload --host 0.0.0.0 --port 8001
lsof -i:8001
uvicorn finalapi:app --reload --host 0.0.0.0 --port 8001
pm2 list
pm2 stop 2
pm2 delete savings-api
uvicorn finalapi:app --reload --host 0.0.0.0 --port 8001
uvicorn finalapi:app --reload --host 0.0.0.0 --port 8003
pm2 start uvicorn --name savings-api --interpreter python3 --   finalapi:app --host 0.0.0.0 --port 8003
ls
cd savings
ls
cd orphaned
ls
nano neworphaneddisk.py 
python3 neworphaneddisk.py
ls
ls
cd savings/
cd orphaned/
ls
python3 blahtest.py
rm neworphaneddisk.py 
rm orphaneddisk.py 
cat blahtest.py 
su postgres
neworphaneddisk.py
nano neworphaneddisk.py
python3 neworphaneddisk.py 
ls
su postgres
cd savings/orphaned/
ls
rm blahtest.py 
nano finalorphanedisk.py
python3 finalorphanedisk.py
cd savings/orphaned/
ls
su postgres
cd savings/orphaned/
ls
rm neworphaneddisk.py 
rm underutilized.py 
cd savings/orphaned/
ls
cat finalorphanedisk.py 
ls
cat costcompliance.py 
cat apicostcompliance.py 
ls
cat ec2startstop_api.py 
ls
nano updcomplianceapi.py
pm2 start uvicorn --name compliance-api --interpreter python3 --   updcomplianceapi:app --host 0.0.0.0 --port 8004

pm2 delete 4
uvicorn from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Optional, Dict
from datetime import date
# -------------------------------
# DB CONFIG
# -------------------------------
DB_CONFIG = {
}
# -------------------------------
# DB HELPER
# -------------------------------
def get_db_connection():
# -------------------------------
# Pydantic Schema for Tag Compliance
# -------------------------------
class TagCompliance(BaseModel):
# -------------------------------
# FastAPI App
# -------------------------------
app = FastAPI(title="AWS Unified API", version="1.0")
# -------------------------------
# SINGLE ENDPOINT TO FETCH BOTH
# -------------------------------
@app.get("/fetch-data")
def fetch_data():
# -------------------------------
# HEALTH CHECK
# -------------------------------
@app.get("/")
def health_check():
q:app --reload --host 0.0.0.0 --port 8001
ls
uvicorn updcomplianceapi:app --reload --host 0.0.0.0 --port 8004
rm updcomplianceapi.py 
ls
nano ec2_autostartstop.py 
cat ec2_autostartstop.py 
ls
cat costcompliance.py 
nano updcomplianceapi.py
uvicorn updcomplianceapi:app --reload --host 0.0.0.0 --port 8004
pm2 start uvicorn --name compliance-api --interpreter python3 --   updcomplianceapi:app --host 0.0.0.0 --port 8004
su postgres
ls
cd savings
cd orphaned/
ls
nano finalapi.py 
su postgres
ls
nano finalapi.py 
pm2 ls
pm2 delete 3
pm2 start uvicorn --name savings-api --interpreter python3 --   finalapi:app --host 0.0.0.0 --port 8003
ls
su postgres
ls
cd savings/
cd orphaned/
ls
nano fastapi.py
ls
nano finalapi.py
pm2 list
pm2 delete 6
pm2 start uvicorn --name savings-api --interpreter python3 --   finalapi:app --host 0.0.0.0 --port 8003
ls
nano finalorphanedisk.py 
cat finalorphanedisk.py 
ls
neworphaneddisk.py
nano neworphaneddisk.py
python3 neworphaneddisk.py
su postgres
ls
cd savings/orphaned/
ls
cat neworphaneddisk.py 
ls
cat orphanedeip.py 
ls
cat orphanedsnapshots.py 
ls
cat updunderutilized.py 
ls
cat finalapi.py 
cd ../..
ls
cat ec2_autostartstop.py 
ls
cat costcompliance.py 
ls
cat updcomplianceapi.py 
ls
cd Dashboard/cd D
cd Dashboard/
ls
cat cm+fm+sb+dc+top5api.py
ls
cd ..
ls
cat apideepdive.py 
ls
cat updmultipleusercur.py 
ls
cat forecast.py
ls
cat updmonthlycurrent.py 
ls
nano updaily_cost.py 
cat updaily_cost.py 
ls
nano updcategorycost.py 
cat updcategorycost.py 
ls
cat serviceStatus.py 
ls
cat tax_support.py 
ls
cat ri_savingsplan.py 
ls
cat monthly_cost.py 
ls
cat deepdive.py
ls
cat customdate.py 
ls
sudo su
sudo  su
sudo su
sudo su
ls
cd Dashboard/
ls
cat cm+fm+sb+dc+top5api.py 
cd Dashboard/
ls
cat cm+fm+sb+dc+top5api.py 
su postgres
ls
cd performance/
ls
rm perf.py
ls
cd ..
ls
cd Dashboard/
ls
cat cm+fm+sb+dc+top5api.py 
ls
cd ..
ls
python3 costcompliance.py 
ls

ls
python3 updmultipleusercur.py 
python3 updmonthlycurrent.py 
ls
python3 updcategorycost.py 
ls
python3 updaily_cost.py 
ls
python3 tax_support.py 
python3 serviceStatus.py 
python3 ri_savingsplan.py 
ls
cd savings/
ls
ls
cd Dashboard/
ls
finaldashboardapi.py
nano finaldashboardapi.py
pm2 list
pm2 delete 0
pm2 start "uvicorn finaldashboardapi:app --host 0.0.0.0 --port 8000" --name finaldashboardapi --interpreter python3
pm2 stop 8
ls
pm2 start "uvicorn cm+fm+sb+dc+top5api:app --host 0.0.0.0 --port 8000" --name finaldashboardapi --interpreter python3
pm2 delete 8
pm2 delete 9
pm2 start "uvicorn cm+fm+sb+dc+top5api:app --host 0.0.0.0 --port 8000" --name finaldashboardapi --interpreter python3
ls
pm2 start "uvicorn cm_fm_sb_dc_top5api:app --host 0.0.0.0 --port 8000" --name cm_fm_sb_dc_top5api --interpreter python3
pm2 delete 10
pm2 delete 11
history
su postgres
ls
cat deepdive.py 
ls
mkdir performance
cd performance/
ls
nano perf.py
python3 perf.py 
rm perf.py 
nano perf.py
python3 perf.py 
rm perf.py 
nano perf.py
python3 perf.py 
su postgres
ls
python3 perf.py 
su postgres
ls
finalperfdormance.py
nano finalperformance.py
python3 perf.py 
python3 finalperformance.py 
su postgres
ls
cd performance/
ls
su postgres
ls
cd Dashboard/
ls
cat cm+fm+sb+dc+top5api.py 
ls
rm finaldashboardapi.py 
nano finaldashboardapi.py
ls
cd Dashboard
ls
cd Dashboard/
ls
cat cm+fm+sb+dc+top5api.py 
cd ..
ls
py updmultipleusercur.py 
python3 updmonthlycurrent.py 
python3 updmultipleusercur.py
ls
python3 updcomplianceapi.py 
python3 updcategorycost.py 
ls
python3 updaily_cost.py 
ls
python3 tax_support.py 
ls
python3 serviceStatus.py 
ls
python3 ri_savingsplan.py 
ls
python3 forecast.py
python3 monthly_cost.py 
ls
python3 ec2_autostartstop.py 
python3 deepdive.py 
ls
python3 costcompliance.py 
ls
cd Dashboard\
cd Dashboard/
ls
cat cm+fm+sb+dc+top5api.py
ls
nano dashboardapi.py
pm2 list
pm2 start "uvicorn dashboardapi:app --host 0.0.0.0 --port 8005" --name lastdashboardapi --interpreter python3
pm2 list
pm2 delete 15
pm2 list
pm2 delete 13
pm2 delete 12
ls
pm2 start "uvicorn dashboardapi:app --host 0.0.0.0 --port 8000" --name dashboardapi --interpreter python3
pm2 list
pm2 delete 14
pm2 start uvicorn --name dashboardapi --interpreter python3 -- dashboardapi:app --host 0.0.0.0 --port 8000
pm2 list
ls
pm2 delete 15
pm2 start uvicorn --name dashboardapi --interpreter python3 -- cm+fm+sb+dc+top5api:app --host 0.0.0.0 --port 8000
pm2 list
ls
cd Dashboard/
ls
cat cm+fm+sb+dc+top5api.py 
cd Dashboard/
ls
pm2 start uvicorn --name dashboardapi --interpreter python3 -- cm+fm+sb+dc+top5api:app --host 0.0.0.0 --port 8000
ls
cd Dashboard/
ls
cat cm+fm+sb+dc+top5api.py 
ls
truncate cm+fm+sb+dc+top5api.py 
rm cm+fm+sb+dc+top5api.py
nano cm+fm+sb+dc+top5api.py
python3 cm+fm+sb+dc+top5api.py
pm2 list
ls
nano cm+fm+sb+dc+top5api.py 
rm cm+fm+sb+dc+top5api.py 
nano cm+fm+sb+dc+top5api.py 
pm2 start uvicorn --name dashboardapi --interpreter python3 -- cm+fm+sb+dc+top5api:app --host 0.0.0.0 --port 8000
pm2 list
cd ..
ls
cd performance
ls
su postgres
ls
cat finalperformance.py 
ls
nano performanceapi.py
pm2 start "uvicorn performanceapi:app --host 0.0.0.0 --port 8005" --name performance-api --interpreter python3
pm2 start "uvicorn performance_api:app --host 0.0.0.0 --port 8005" --name performance-api --interpreter python3
pm2 list
pm2 delete 18
pm2 delete 19
pm2 list
pm2 delete 17
ls
pm2 delete 16
pm2 start "uvicorn performanceapi:app --host 0.0.0.0 --port 8005" --name performance-api --interpreter python3
pm2 list
ls
cd ..
ls
cd Dashboard/
ls
LS
ls
pm2 list
history
cd Dashboard/
ls
pm2 list
pm2 delete 21
pm2 list
cd ..
ls
cd performance/
ls
pm2 list
pm2 delete 20
pm2 list
ls
pm2 delete 23
pm2 delete 24
pm2 start "uvicorn performanceapi:app --host 0.0.0.0 --port 8001" --name performance-api --interpreter python3
pm2 list
pm2 logs performance-api
pm2 start uvicorn --name performance-api --   performanceapi:app --host 0.0.0.0 --port 8001
pm2 delete 25
cat performanceapi.py 
cd ..
ls
nano performanceapi.py
pm2 start uvicorn --name performance-api --interpreter python3 -- performanceapi:app --host 0.0.0.0 --port 8001
pm2 delete 26
pm2 list
cat performanceapi.py 
pm2 start uvicorn --name performance-api --   performanceapi:app --host 0.0.0.0 --port 8001
pm2 delete 27
pm2 delete 28
pm2 start uvicorn --name Performance_api --interpreter python3 -- performanceapi:app --host 0.0.0.0 --port 8008
pm2 list
ls
cat performanceapi.py 
sudo su
ls
cat forecast.py
ls
nano forecast.py
ls
pm2 list
cd performance/
ls
cat performanceapi.py 
history
cat performanceapi.py 
sudo su
sudo su
ls
cat forecast.py
su postgres
ls
cat tags.py
nano tags.py
python3 tags.py
rm tags.py
nano tags.py
history
python3 tags.py 
ls
rm tags.py 
nano tags.py
python3 tags.py 
ls
nano finaltag.py
python3 finaltag.py 
su postgres
ls
rm finaltag.py 
nano finaltag.py
python3 finaltag.py 
su postgres
ls
python3 finaltag.py 
su postgres
ls
tagsapi.py
nano tagsapi.py
history
pm2 start uvicorn --name tags_api --interpreter python3 -- tagsapi:app --host 0.0.0.0 --port 8007
pm2 list
nano tagsapi.py 
pm2 delete 30
pm2 start uvicorn --name tags_api --interpreter python3 -- tagsapi:app --host 0.0.0.0 --port 8007
pm2 list
ls
ls
python3 updmultipleusercur.py 
ls
python3 updmonthlycurrent.py 
python3 updcomplianceapi.py 
python3 updcategorycost.py 
ls
python3 updaily_cost.py 
ls
python3 serviceStatus.py 
python3 tax_support.py 
ls
python3 ri_savingsplan.py 
ls
python3 forecast.py 
python3 finaltag.py 
ls
cd Dashboard/
ls
history
ls
pm2 list
cd ..
ls
cd Dashboard/
ls
su postgres
cat dashboardapi.py 
nano finaldashboardapi.py
uvicorn finaldashboardapi:app --reload --host 0.0.0.0 --port 8007
uvicorn finaldashboardapi:app --reload --host 0.0.0.0 --port 8010
rm finaldashboardapi.py 
ls
cat dashboardapi.py 
nano finaldashboardapi.py
uvicorn finaldashboardapi:app --reload --host 0.0.0.0 --port 8010
ls
cat dashboardapi.py 
ls
rm finaldashboardapi.py 
nano finaldashboardapi.py
uvicorn finaldashboardapi:app --reload --host 0.0.0.0 --port 8010
su postgres
ls
rm finaldashboardapi.py 
nano finaldashboardapi.py 
uvicorn finaldashboardapi:app --reload --host 0.0.0.0 --port 8010
ls
cat finaldashboardapi.py 
uvicorn finaldashboardapi:app --reload --host 0.0.0.0 --port 8010
pm2 list
history
pm2 start uvicorn --name modifiedDashboard_api --interpreter python3 -- finaldashboardapi:app --host 0.0.0.0 --port 8010
pm2 list
sudo su
ls
python3 updaily_cost.py 
ls
python3 updmultipleusercur.py 
ls
python3 updmonthlycurrent.py 
cat updcategorycost.py 
python3 updcategorycost.py 
ls
python3 tax_support.py 
python3 serviceStatus.py
ls
python3 serviceStatus.py
python3 forecast.py 
ls
python3 finaltag.py
ls
python3 ec2_autostartstop.py 
python3 deepdive.py 
ls
cd savings/
ls
cd orphaned/
ls
python3 finalorphanedisk.py 
ls
python3 orphanedeip.py 
ls
python3 orphanedsnapshots.py 
ls
python3 updunderutilized.py 
ls
cd ..
ls
cd ..
ls
cd Dashboard/
ls
cat finaldashboardapi.py 
ls
cd Dashboard/
ls
nano newfinaldashboardapi.py
pm2 start uvicorn --name modifiedDashboard_api --interpreter python3 -- newfinaldashboardapi:app --host 0.0.0.0 --port 8005
pm2 list
sudo su
ls
cd savings
ls
cd orphaned/
ls
cat finalapi.py 
su postgres
ls
nano newfinalapi.py
pm2 list
pm2 delete 35
pm2 delete savings-api
pm2 start uvicorn --name savings_api --interpreter python3 -- newfinalapi:app --host 0.0.0.0 --port 8003
su postgres
ls
nano orphanedeip.py 
pm2 list
ls
nano newfinalapi.py 
pm2 delete 36
pm2 start uvicorn --name savings_api --interpreter python3 -- newfinalapi:app --host 0.0.0.0 --port 8003

pm2 delete 37
pm2 start uvicorn --name savings_api --interpreter python3 -- newfinalapi:app --host 0.0.0.0 --port 8003
cd ..
ls
cd ubuntu
ls
cd Dashboard
ls
python3 forecast.py 
nano forecast.py 
su postgres
nano forecast.py 
python3 forecast.py 
ls
cd Dashboard/
ls
rm newfinaldashboardapi.py 
nano newfinaldashboardapi.py 
pm2 list
pm2 start uvicorn --name finalDashboard_api --interpreter python3 -- newfinaldashboardapi:app --host 0.0.0.0 --port 8005
cd ..
ls
nano updmonthlycurrent.py 
su postgres
ls
nano updmonthlycurrent.py 
python3 updmonthlycurrent.py 
ls
cat updmonthlycurrent.py 
su postgres
ls
newupdmonthlycurrent.py
nano newupdmonthlycurrent.py
python3 newupdmonthlycurrent.py 
ls
cat updmultipleusercur.py 
su postgres
cat newupdmonthlycurrent.py 
ls
cat updaily_cost.py 
ls
cat updmonthlycurrent.py 
ls
cat newupdmonthlycurrent.py 
ls
cat newupdmonthlycurrent.py 
ls
nano monthlycurrrrrrrrrrrrrrrrrrrentcost.py
python3 monthlycurrrrrrrrrrrrrrrrrrrentcost.py 
su postgres
ls
rm monthlycurrent.py
rm updmonthlycurrent.py 
ls
ls
mkdir V1proj
rmdir V1proj/
rmdir v1proj/
mkdir v1proj
ls
cd v1proj/
ls
sudo su
ls
cd v1proj/
ls
sudo su
cat daily_cost.py 
su postgres
ls
cat daily_cost.py 
uptime
w
curl ifconfig.me
sudo su
su postgres
ls
cd v1proj/
ls
cat organisation.py
nano organisation.py
rm organisation.py 
nano organisation.py
cat organisation.py 
ls
nano organisation.py
su postgres
ls
nano organisation.py 
vi organisation.py 
ls
nano .env
chmod 600 .env
pip install boto3 pandas psycopg2-binary python-dotenv pyarrow
ls
python3 organisation.py 
ls
nano organisation.py 
cat organisation.py 
sudo su'
sudo su
ls
cd v1proj/
ls
rm organisation.py 
nano organisation.py
python3 organisation.py 
ls
cd v1proj/
la
ls
cat organisation.py 
