This project has been deployed at:
```
https://photo-timeline-182004.appspot.com/
```


To run this as a local development server, use the following command:
```
dev_appserver.py --default_gcs_bucket_name <Cloud Storage Bucket Name> ./
```


#### Curl Commands

1. **Authenticate User** (Returns user's id_token)
```
curl -v https://photo-timeline-182004.appspot.com/user/authenticate/?username=<username>&password=<password>
```

2. **Post a Picture**
```
curl -v -X POST -H "Content-Type: multipart/form-data" -F caption=<caption> -F "image=@<image file path>" https://photo-timeline-182004.appspot.com/post/<username>/?id_token=<id_token>
```

3. **Get a json list of most recent submitted pictures** (Returns information including image url (relative path))
```
curl -v https://photo-timeline-182004.appspot.com/user/<username>/json/?id_token=<id_token>
```

4. **Download a specific picture** (Saves image into output file)
```
curl https://photo-timeline-182004.appspot.com/<image uri>/?id_token=<id_token> > <output filename>
```

5. **Delete a specific picture**
```
curl -v https://photo-timeline-182004.appspot.com/<image uri>/delete/?id_token=<id_token>
```

