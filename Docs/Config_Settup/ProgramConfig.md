# Program config file settup

### Valid config sections.
The parameter order does not matter.
* **Logging**
    * **log_verbosity**
        * **DEBUG**
        * **INFO**
        * **WARNING**
        * **ERROR**
        * **CRITICAL**
        Sets global logging level. The default level is WARNING,
            if not declared or set to an unsupported value.
            This means that only events of this level and above will be tracked.
            

    * **log_file_size_limit: Sets max log file size in KB. Defaults to 20MB.**

Here is what the default ProgramConfig.ini looks like.
```ini
[Logging]
log_verbosity = DEBUG
log_file_size_limit = 20000
```