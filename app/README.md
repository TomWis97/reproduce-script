# Health Check Script
Dit is een script om de gezondheid van het platform te monitoren.

## Welke stappen voert het script uit?
Gebaseerd op [de documentatie](https://docs.openshift.com/container-platform/3.11/day_two_guide/environment_health_checks.html) doet het de volgende stappen:
1. Het maakt een project aan.
2. Secret aanmaken voor git clone.
3. Secret linken aan serviceaccount voor git clone.
4. In dat project wordt een source-to-image build gemaakt.
5. De buildconfig wordt aangepast zodat er gelinkt wordt naar de pull secret.
6. Het checkt of de build succesvol is en of de uiteindelijke pod draait.
7. Via de loadbalancer vraagt het een pagina op vanuit de nieuwe pod.
8. Het net aangemaakte project wordt weer verwijderd.

Daarnaast checkt het de volgende dingen:
9. Kijk of alle routers nog draaien.
10. Kijk of alle nodes "Ready" zijn.
11. Kijk of alle CNS nodes van beide Gluster clusters elkaar als "Online" zien.

Nog te implementeren checks:
- Of filesystems niet zijn volgelopen.

## API calls
Welke API calls moeten voor de stappen gemaakt worden?

Headers voor requests:

| Key              | Value                       |
|------------------|-----------------------------|
| Accept           | application/json, \*/\*     |
| User-Agent       | health-check-script/v0.1    |
| Authorization    | Bearer <TOKEN>              |
| Content-Type     | application/json            |

1. Project aanmaken:   
   Type: `POST`   
   URL: `/apis/project.openshift.io/v1/projectrequests`
```json
{"kind":"ProjectRequest","apiVersion":"project.openshift.io/v1","metadata":{"name":"health-check","creationTimestamp":null}}
```

2. Secret aanmaken:   
   Type: `POST`   
   URL: `/api/v1/namespaces/health-check/secrets`   
```json
{"apiVersion":"v1","data":{"ssh-privatekey":"LS0tLS1CRUdJTiBSU0EgUFJJVkFURSBLRVktLS0tLQpNSUlKS1FJQkFBS0NBZ0VBdVBkT3VsL2RuVEpqNDdaZlJLR3QxdWQ4SG9WMkg4cHQ1b0VBU2p5Z2pQMFpDUlEvCnJMYStnZVpQY0tHM2d0eXFUL1Rzc2lFclY2TzNCWmtNY25GZWx5QmJHam9xTmhVN0NjSWRtWDVVOXZMdklxMlgKSTRrUi9MWDMrVGZXUmx6UWdReDRrU21leFFJL01hbVd0YTl3dWZCOW0xbm1WOVBlcU1LbFFaNms3VnVxVmN4bwo3OUhuMmpsbGlpTzJPYmsrWnNrdFVWemFrQWFMaW9jSXkyRG50eFI4UTMxTzdYSUZ0VDVMNUc2ZUZaV3JmR2x1Clh3VXVaalBVWXlYWGlJNEljWVJMbnY5QUJZLy9QK3UxVHNuZjhVODI1QWhuaFpqZjE4aWJ0dEZjZVJ2YjNYOTAKd1kxZit0TjFIWGlaSGVtQ29xVmVvdFp3a1hhcG91UkloMEcvZmp3bXhRdDlLVGJuVzJJM3NWaXhwYmxPWUh4VQpiRkNmUnAyL3JzaS9VZXU1blZpS2doaEpXc0V3cU5FdWxmdWpJQllXSWEyUERBR3d2cGZZNDdrYjFqT3FJVGNoCnRKbC8rbFdZOTNoVWV6L1ZCVmx3L1k0dG5lekFub0NKYzQvazAzbFk3YWRvRytpeENHQjVXOURSSUJxTk5VOXgKTmNMcDhRTi94ZXNLVWJRK2Q5Kyt2NzBwdG1BRWxLUlVGSnlzWisvaURhMDNRUUUzekNYY0ZZOVJHbXNWaVlzawpCQ1ZvQ2ZHbndlYTl4SGpCWFdxeWVXK3FPMU5OYnJBT3RLdTByLzl1ejk2VVhGcUpMYnkvNTJXRkJuOUROblVwCk1VdUR4MnMxMkV5KzZwc2ZpOW0xMVlGUkR1SXZRRVlMMVNXT3Q3MnNWMy9mZmlPWVJWNWZBVXBpUjFzQ0F3RUEKQVFLQ0FnQjYxZXBYeFlDRWU4bHdtVlhOVzEzNllVTEJkanFMUkVFV0drZWFCWWROK211YzV2Q2VmOEltdkUrMwphZjVZRHJtZ1hmU3ZHMjRRUnE0dUxvVGduNytFdDcwb3ZzWDNvc1BSYURPR0V5clQwV1BVY05uMWhIc0lpOFJCCm9yNVBmaVlOL2IwNEVoN1prUE5zeE1aTXBGVkZkcHZFQnNEOVJMd1M4U2tVV2dvSGc1K3NXUks3YVhnREthancKUTJVcUVvYUpka0w5VEovdGxCc3BoU0huQnRUN2RjUk1nYlJmNWlBNlRFUFVVVTMwNGErLzhMaVdxL2N6Y21veQo2aGVvSFVNb09BYU1jZEVQb0tDUHo3Wlp1NkZZUFJZai9CemIwVG1lc1NBUUdodkNaaWp1Z1UyRm1LRE1ENUF3CllUMjJhclFSMWFieWwxeXNqZFI4VkFTQ3ByeEhNekh0MWllWGdQNkV4ZktRUnFaSHJxYURVRXZqR0hvZTBEajYKOGU3MGZzOC9lQ3RGM1BrOEw1NG9XVnBaSGw0V09UQVRSMnZGMHZmamFTT0QyclJtNk1rMDJkVTFtWFl2NkN1LwpJSFAyYVpFdm1wQWhtdVNWS2ZqS0RmVTVsOG5tZy9uZjFXS0h4Zi93enhvdkJrdWNFUHUxemdqQzQ0aVZFbU9rCjRvTGFNenRaNlJtc1Jwd3U2TUFoSUxlU3VFU2ZZY2pDcnhLL3gwTHgrcFM1UmZZdUU1WWFHZnNEVFlBdnYwOWsKL2phU3ltNmFvTk5wN0N6c091K016WERuYi9RM1ZSb3hhNi8vcGZBN3c1SkR4QmIxU0Q5bjJDTXRxZFAxMmRIMwpsZmhzM0dHRWtlUzg5SWpOSEVlSCtsSEhkdGJhbDhxRXp0Q0RIVTMyMll5UlBzNE4rUUtDQVFFQTlEY29zb1NDCjFwZ3ozeUdONWozUmtlWGFJUXUzZHJUbHh2V0xTMTRFUFo0VDJEelV0bUxQZXhXeVhVVEZnVlZTcEJUUlZzR0YKd3cvSnNYaEgyL2hhOEFCWUpOVkU3Z0JOaHA4S3Q1WXZBUE5VTjAwbmI2bmF5V3pZTFNZQ1hpaVlQTTFsUGJSawpGVEhlaEFmcU1lNnFxT1ZiSUxPUDF5V0V2Z0dBYUdtYU1GNE9MUHlxL1VrOUxHb0hmZ3A5c0xSWmFpS2ZOZ0hYCmFwMVNUdkxBdjVxam5nK1ErdFR4L01iclhLZHlkOE0zbHFYNUNFZXArdWpOdWlGN0xmeHVGZC9IbXFwdEhhUDEKdUo1OG1BeUdBS2RkalJUelNWNUVRdHNKZlN1SlZyQ1ZaeVhtRUlIZXBObGtMOGREQ1pCcUwzOEd1YnhTWFlQUAorN1hBbk5tQXpFZTM5d0tDQVFFQXdlUTZubFdtd1Uxb3BXQlIvVnQxTnIzTHJxMVZIdEkvc3JlQ2I4bVpmL0tTCjF0b1hSNUVHaE9la2xiZjZ6OUlCOEtwTXAzQXFLSXl5YllpQUVIK056QmFqam1JLzg1elhhTXFPUlI4M0tWK3EKSXFRNkFCcWF2aythc0dYbHg4QmUyTGJmUnFZOFYrT29ZQ3RkbFh0RkJyTWNqOVl3SlI2UGFwQWRvVGNwUDN2bApPL0g3UG1VVU1ubGlQMTZ0L0YybTIwdENvbVd4UGZ0VG9KVG5GZU01dDkxcXNNNVRRRTZsci95YjE2SUQ1Z1dsCmJpek1hV0Y4TzhNRFRwc252YjRqRi9ValhWZnRWZGlpMmZQblJ0MFpWa21UM2tHNENaVzNPRWNEZllGaWZGQ2wKMUtFNmJuRHdudnJ4T0diR0FST0pKTXlpK1d4OFJhY2xNZDYvK3VxNnZRS0NBUUVBaGpkeVpIb3pOaUU4RU50dQpFeVhTY2E2emJRbjFjSVlHNm91MFhGMTFVeS8zbEJZS2lacFFrVUxoWGlVWHJ2Ym5qa25xcXhWOG9ER2pGYWdYClJpdCtQdnpSZEp6SlgweEhUejlGTXBTVmpKNHVvSjRFbUhmdlNGaExqclNmQklTbTluT2p1bi9UcVZwWkFwTWYKQVFZOFFNcWNoS0pxNFVFN2JQbUNTdUFPMzVveGpFUG83WDg4NFpYOFBDY2o0T09kYUpsU2l1b0VMQkgrVkdsUgp5WHdCaERMbDZSVHpVWXM1ZXhpRDdwSVprTy95cDd4TERSeTVSQngyaUZWOVl3UXp2U3NCQVJORlRvdTd5Z3pICjhNQUt5Q2pGZElNY1hPbm9reVJFUEtLYjJhNllmR1lEcVBIWS8vRXhSS1piMVhLb2paZVVaTlMyajQzYUo5bloKMFd0eERRS0NBUUJoazlDRVdxcWZZYXVtZnNFRWRvQ1kyZytsaXducGh2b1RvUkw5MjBGckNOTXBXWHlad2J5OApLaS9FUVdEeU1jaFVMQUNEeTRrTCt6TFl1UGRxVmljd2JMeEhMZDd0WlNOclUzVWlDRUdraXNaK3hKT0Q5ZCttCm96MUFSU2ZNelYxdVJ5bzZ6ZkpVY1BnTjNnVXM4MnFib294ZlB2WGYyRzlvdTdxTnBjc1diZTNCcTFnNzRIYTMKcUNydnBXQitQMHQzMVhwbGJEUTA4MFQwN2JzV1l0SnJXLzBUbWVKLzNKUzU2ckVyWmhmOExSOUNRVDFtVTI5SQpUQzVmNHVtdkxmOVBVVWxJOHJVNG5Odm9RRDFHaG9MM3ovT2d5UVlybkxNbW1XYUNSUmtoWXh6eDAyb3FwcUFTCkFreGZqQ2xkNVUwQnZoTE8zKy95eGRtTUxZUUViUmtwQW9JQkFRQzRPYUJFd3FUQVZDbDB5TENueHNYYkpTUnMKWGxYWXRkTU96TjFhUGRyQVdVeFFtcndRZVVWa1JBVWJDUlpvT2YyOG1tK1hSMkRBM25YM1NNcElyWEYzMlVzYgpSeW9oZ3Q0WENLUm5xcnVCZ1pGTEUyTVZyZkxVTU9IZGx1aGUwRXpqMWRESzJHSVJHdTMxdDF3OExJVEdma1N5Cko1YjZPUFA3OW1hQzBmS3hBQ1d4TlM2SWd6QnpzWnJ6UE96cUd5ZWFIM3dyclR6Z0szaDZWWGpzQmhxOUJGbG4KeFJETFFKKy85dGtOM1JPa1NMWi9NT3BlREtaQkV4OWRQeWVBSGhDV25ockxVa1BVaUJFQkROT0FqSnJyd2gvMwpEVWYzRFByM1ErSG1GVW1xUU9CaC9CVkRwMUFyRUV6TnYwbVFjQjJVWHpleUJ3TUY2elJiY3A0ZzZ1eUQKLS0tLS1FTkQgUlNBIFBSSVZBVEUgS0VZLS0tLS0K"},"kind":"Secret","metadata":{"creationTimestamp":null,"name":"deploy-key"}}
```

3. Secret linken aan serviceaccount:   
`GET` naar `/api/v1/namespaces/health-check/serviceaccounts/builder`.   
De response moet bewerkt worden. In het antwoord onder de list "secrets" een dictionary toevoegen met key `name` en value `deploy-key`.   

`PUT` van de aangepaste json naar `/api/v1/namespaces/health-check/serviceaccounts/builder`.

4. Source-to-image build maken.   
ImageStream aanmaken:   
Type: `POST`   
URL: `/apis/image.openshift.io/v1/namespaces/health-check/imagestreams`
```json
{"apiVersion":"image.openshift.io/v1","kind":"ImageStream","metadata":{"annotations":{"openshift.io/generated-by":"OpenShiftNewApp"},"creationTimestamp":null,"labels":{"app":"health-check-script"},"name":"health-check-script"},"spec":{"lookupPolicy":{"local":false}},"status":{"dockerImageRepository":""}}
```

BuildConfig aanmaken:   
Type: `POST`   
URL: `/apis/build.openshift.io/v1/namespaces/health-check/buildconfigs
```json
{"apiVersion":"build.openshift.io/v1","kind":"BuildConfig","metadata":{"annotations":{"openshift.io/generated-by":"OpenShiftNewApp"},"creationTimestamp":null,"labels":{"app":"health-check-script"},"name":"health-check-script"},"spec":{"nodeSelector":null,"output":{"to":{"kind":"ImageStreamTag","name":"health-check-script:latest"}},"postCommit":{},"resources":{},"source":{"contextDir":"webpage","git":{"uri":"<github repo>"},"type":"Git"},"strategy":{"sourceStrategy":{"from":{"kind":"ImageStreamTag","name":"php:7.1","namespace":"openshift"}},"type":"Source"},"triggers":[{"github":{"secret":"wtx8ZEEesNK-qBSAmbqt"},"type":"GitHub"},{"generic":{"secret":"ZQIAXBSDgH-yrJkuSztb"},"type":"Generic"},{"type":"ConfigChange"},{"imageChange":{},"type":"ImageChange"}]},"status":{"lastVersion":0}}```
`` 

DeploymentConfig aanmaken:   
Type: `POST`   
URL: `/apis/apps.openshift.io/v1/namespaces/health-check/deploymentconfigs`
```json
{"apiVersion":"apps.openshift.io/v1","kind":"DeploymentConfig","metadata":{"annotations":{"openshift.io/generated-by":"OpenShiftNewApp"},"creationTimestamp":null,"labels":{"app":"health-check-script"},"name":"health-check-script"},"spec":{"replicas":1,"selector":{"app":"health-check-script","deploymentconfig":"health-check-script"},"strategy":{"resources":{}},"template":{"metadata":{"annotations":{"openshift.io/generated-by":"OpenShiftNewApp"},"creationTimestamp":null,"labels":{"app":"health-check-script","deploymentconfig":"health-check-script"}},"spec":{"containers":[{"image":"health-check-script:latest","name":"health-check-script","ports":[{"containerPort":8080,"protocol":"TCP"},{"containerPort":8443,"protocol":"TCP"}],"resources":{}}]}},"test":false,"triggers":[{"type":"ConfigChange"},{"imageChangeParams":{"automatic":true,"containerNames":["health-check-script"],"from":{"kind":"ImageStreamTag","name":"health-check-script:latest"}},"type":"ImageChange"}]},"status":{"availableReplicas":0,"latestVersion":0,"observedGeneration":0,"replicas":0,"unavailableReplicas":0,"updatedReplicas":0}}
```

Service aanmaken:   
Type: `POST`   
URL: `/api/v1/namespaces/health-check/services`
```json
{"apiVersion":"v1","kind":"Service","metadata":{"annotations":{"openshift.io/generated-by":"OpenShiftNewApp"},"creationTimestamp":null,"labels":{"app":"health-check-script"},"name":"health-check-script"},"spec":{"ports":[{"name":"8080-tcp","port":8080,"protocol":"TCP","targetPort":8080},{"name":"8443-tcp","port":8443,"protocol":"TCP","targetPort":8443}],"selector":{"app":"health-check-script","deploymentconfig":"health-check-script"}},"status":{"loadBalancer":{}}}
```

Route aanmaken:   
Type: `POST`   
URL: `/apis/route.openshift.io/v1/namespaces/health-check/routes`
```json
{"apiVersion":"route.openshift.io/v1","kind":"Route","metadata":{"creationTimestamp":null,"labels":{"app":"health-check-script"},"name":"health-check-script"},"spec":{"host":"","port":{"targetPort":"8080-tcp"},"to":{"kind":"","name":"health-check-script","weight":null}},"status":{"ingress":null}}
```

5. Secret linken aan BuildConfig: Bij het aanmaken van de BuildConfig moet er onder spec.source.sourceSecret.name verwezen worden naar de naam van de eerder aangemaakte secret.

6. Herhaaldelijk een `GET` doen op `/api/v1/namespaces/health-check/pods`. Hierbij krijg je een json terug die begint met een dictionary. Per pod in het project heb je een item in `rows`. Kijk hierbij naar de `cells` key. De eerste drie items in deze list zijn relevant: [0] is de naam van de pod, [1] is hoeveel er ready zijn (bijv "1/1") en [2] is de staat.   
De volgende stappen worden hierbij doorlopen:
- Een pod met `-build`:
  - `Pending`
  - `Init:0/2`
  - `Init:1/2`
  - `PodInitializing`
  - `Running`
  - `Completed`
- Een pod met `-deploy`:
  - `Pending`
  - `ContainerCreating`
  - `Running`
  - `Completed`
  - `Terminating`
- Een pod met een random suffix:
  - `Pending`
  - `ContainerCreating`
  - `Running`

Uiteindelijk moet het aantal ready van de niewste pod "1/1" zijn.

## Installatie
Machine voorbereiden:
```bash
yum install -y python3-requests
```
