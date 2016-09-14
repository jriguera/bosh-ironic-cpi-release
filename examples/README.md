# Files for some manual checks

The purpose is just check if the job is working, configuration files created, ... It is only for testing!


# Scripts

Run these scripts from the parent folder!

 * `bosh_prepare`: Downloads the src tarfiles from the comments on the package spec definition, 
but if a prepare script is present, run it and skip the spec. In the spec file should be a 
comment with the URL of the package.
 * `make_manifest`: Create a test manifest (for warden)
