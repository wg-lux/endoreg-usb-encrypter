{
  description = "Flake for the Django based `endoreg-usb-encrypter`application";

  nixConfig = {
    substituters = [
        "https://cache.nixos.org"
      ];
    trusted-public-keys = [
        "cache.nixos.org-1:6NCHdD59X431o0gWypbMrAURkbJ16ZPMQFGspcDShjY="
      ];
    extra-substituters = "https://cache.nixos.org https://nix-community.cachix.org";
    extra-trusted-public-keys = "cache.nixos.org-1:6NCHdD59X431o0gWypbMrAURkbJ16ZPMQFGspcDShjY= nix-community.cachix.org-1:mB9FSh9qf2dCimDSUo8Zy7bkq5CX+/rkCWyvRCYg3Fs=";
  };

  inputs = {
    poetry2nix.url = "github:nix-community/poetry2nix";
    poetry2nix.inputs.nixpkgs.follows = "nixpkgs";


    cachix = {
      url = "github:cachix/cachix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { nixpkgs, poetry2nix, ... } @ inputs: 
  let 
    system = "x86_64-linux";
    self = inputs.self;
    version = "0.1.${pkgs.lib.substring 0 8 inputs.self.lastModifiedDate}.${inputs.self.shortRev or "dirty"}";
    python-version = "311";
    cachix = inputs.cachix;

    pkgs = import nixpkgs {
      inherit system;
      config = {
        allowUnfree = true;
      };
    };

    lib = pkgs.lib;

    pypkgs-build-requirements = {
      gender-guesser = [ "setuptools" ];
      conllu = [ "setuptools" ];
      janome = [ "setuptools" ];
      pptree = [ "setuptools" ];
      wikipedia-api = [ "setuptools" ];
      django-flat-theme = [ "setuptools" ];
      django-flat-responsive = [ "setuptools" ];
      pypdfium2 = [ "setuptools" ];
    };

    poetry2nix = inputs.poetry2nix.lib.mkPoetry2Nix { inherit pkgs;};

    p2n-overrides = poetry2nix.defaultPoetryOverrides.extend (final: prev:
      builtins.mapAttrs (package: build-requirements:
        (builtins.getAttr package prev).overridePythonAttrs (old: {
          buildInputs = (old.buildInputs or [ ]) ++ (
            builtins.map (pkg:
              if builtins.isString pkg then builtins.getAttr pkg prev else pkg
            ) build-requirements
          );
        })
      ) pypkgs-build-requirements
    );

    poetryApp = poetry2nix.mkPoetryApplication {
      projectDir = ./.;
      src = lib.cleanSource ./.;
      python = pkgs."python${python-version}";
      overrides = p2n-overrides;
      preferWheels = true; # some packages, e.g. transformers break if false
      propagatedBuildInputs =  with pkgs."python${python-version}Packages"; [
        
      ];
      nativeBuildInputs = with pkgs."python${python-version}Packages"; [
        pip
        setuptools
      ];
      buildInputs = with pkgs; [
        poetry
        python311Packages.venvShellHook 
      ];
      venvDir = ".venv";
    };

    poetryEnv = poetry2nix.mkPoetryEnv {
      projectDir = ./.;
      python = pkgs."python${python-version}";
      extraPackages = (ps: [
        ps.pip
      ]);
      overrides = p2n-overrides;
      editablePackageSources = {
     };
      preferWheels = true;
    };
    
  in
  {

    packages.x86_64-linux.poetryApp = poetryApp;
    packages.x86_64-linux.default = poetryApp;
    
    apps.x86_64-linux.celery-beat = {
      type = "app";
      program = "${poetryApp}/bin/celery-beat";
    };

    apps.x86_64-linux.celery-worker = {
      type = "app";
      program = "${poetryApp}/bin/celery-worker";
    };

    apps.x86_64-linux.django-server = {
      type = "app";
      program = "${poetryApp}/bin/django-server";
    };

    apps.x86_64-linux.default = self.apps.x86_64-linux.django-server;
  
    devShells.x86_64-linux.default = pkgs.mkShell {
      buildInputs = [
        pkgs.poetry

        poetryEnv
        pkgs.python311Packages.numpy
        pkgs.python311Packages.venvShellHook

      ];
      venvDir = ".venv";

      # DJANGO SETTINGS
      # DJANGO_SETTINGS_MODULE="agl_monitor.settings_dev";
      DJANGO_SETTINGS_MODULE="agl_monitor.settings_prod";
      DJANGO_DEBUG=true;
      DJANGO_SECRET_KEY="change-me";

      # CELERY SETTINGS
      CELERY_BROKER_URL="redis://localhost:6382/0";
      CELERY_RESULT_BACKEND="redis://localhost:6382/0";
      CELERY_ACCEPT_CONTENT="application/json";
      CELERY_TASK_SERIALIZER="json";
      CELERY_RESULT_SERIALIZER="json";
      CELERY_TIMEZONE="UTC";
      CELERY_BEAT_SCHEDULER="django_celery_beat.schedulers:DatabaseScheduler";
      CELERY_SIGNAL_LOGFILE="/etc/custom-logs/agl-monitor-celery-signal.log";

    };

    ## AGL Anonymizer Module
    nixosModules = {
      agl-monitor = { config, pkgs, lib, ...}: 
        let
          mkOption = lib.mkOption;
        in
      {
        ## Options
        options.services.agl-monitor = {
          enable = mkOption {
            default = false;
            description = "Enable the AGL Monitor service";
          };

          config-json-file = mkOption {
            type = lib.types.str;
            default = "/etc/agl-monitor.json";
            description = "The path to the configuration file for the AGL Monitor service";
          };

          user = mkOption {
            type = lib.types.str;
            default = "logging-user";
            description = "The user under which the AGL Monitor Server will run";
          };

          group = mkOption {
            type = lib.types.str;
            default = "service-user";
            description = "The group under which the AGL Monitor Server will run";
          };

          setup-script = mkOption {
            type = lib.types.anything;
            default = "echo 'No setup script defined'";
            description = "The script which sets up the AGL Monitor service";
          };

          setup-script-name = mkOption {
            type = lib.types.str;
            default = "agl-monitor-pre";
            description = "The name of the setup script";
          };

          custom-logs-dir = mkOption {
            type = lib.types.str;
            default = "/etc/custom-logs";
            description = "The directory where the AGL Monitor logs will be stored";
          };

          django-debug = mkOption {
            type = lib.types.bool;
            default = true;
            description = "Enable Django debug mode";
          };

          django-settings-module = mkOption {
              type = lib.types.str;
              default = "agl_monitor.settings_prod";
              description = "The settings module for the Django application";
            };

          django-port = mkOption {
            type = lib.types.int;
            default = 9243;
            description = "The port on which the Django server will listen";
          };

          django-secret-key = mkOption {
            type = lib.types.str;
            default = "change-me";
            description = "The secret key for the Django application";
          };

          # Define the address on which the Django server will listen
          bind = mkOption {
            type = lib.types.str;
            default = "localhost";
            description = "The address on which the Django server will listen";
          };

          redis-port = mkOption {
            type = lib.types.int;
            default = 6382; #FIXME: currently isnt used, the port is currently defined via config file (agl-monitor.json)
            description = "The port on which the Redis server will listen"; 
          };

          redis-bind = mkOption {
            type = lib.types.str;
            default = "127.0.0.1";
            description = "The address on which the Redis server will listen";
          };

          user-dir = mkOption {
            type = lib.types.str;
            default = "/etc/logging-user";
            description = "The directory where the AGL Monitor user files will be stored";
          };

          service-dir = mkOption {
            type = lib.types.str;
            default = "/etc/logging-user/agl-monitor";
            description = "The directory where the AGL Monitor service will be stored";
          };


          conf = mkOption {
            type = lib.types.attrsOf lib.types.anything;
            default = {
              CACHES = {
                "default" = {
                  BACKEND = "django_redis.cache.RedisCache";
                  LOCATION = "redis://localhost:6382/0";
                  TIMEOUT = "300";
                  OPTIONS = {
                    "CLIENT_CLASS" = "django_redis.client.DefaultClient";
                  };
                };
              };
              CELERY_BROKER_URL = "redis://localhost:6382/0";
              CELERY_RESULT_BACKEND = "redis://localhost:6382/0";
              CELERY_ACCEPT_CONTENT = "application/json";
              CELERY_TASK_SERIALIZER = "json";
              CELERY_RESULT_SERIALIZER = "json";
              CELERY_TIMEZONE = "UTC";
              CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler";

              CELERY_SIGNAL_LOGFILE = "/etc/custom-logs/agl-monitor-celery-signal.log";
            };
            description = "Other settings";
          };


        };

        # Service Implementation
        
        config = lib.mkIf config.services.agl-monitor.enable {

          # Create Redis Server

          services.redis.servers."agl-monitor" = {
            enable = true;
            bind = config.services.agl-monitor.redis-bind;
            port = config.services.agl-monitor.redis-port;
            settings = {};
          };

          # Create Celery Service
          systemd.services.agl-monitor-celery = {
            description = "AGL Monitor Celery Service";
            after = [ "network.target" ];
            wantedBy = [ "multi-user.target" ];
            serviceConfig = {
              ExecStart = "${poetryApp}/bin/celery-worker";
              Restart = "always";
              RestartSec = "5";
              # WorkingDirectory = ./.; REQUIRED?!
              User = config.services.agl-monitor.user;
              Group = config.services.agl-monitor.group;
              
            };
            # script = ''
            #     nix develop
            #     exec celery -A agl_monitor worker --loglevel=info
            #   '';
          };

          # Create Celery Beat Service

          systemd.services.agl-monitor-celery-beat = {
            description = "AGL Monitor Celery Beat Service";
            after = [ "network.target" ];
            wantedBy = [ "multi-user.target" ];
            serviceConfig = {
              ExecStart = "${poetryApp}/bin/celery-beat";
              Restart = "always";
              RestartSec = "5";
              # WorkingDirectory = ./.; REQUIRED?!
              User = config.services.agl-monitor.user;
              Group = config.services.agl-monitor.group;
              Environment = [];
            };
            # script = ''
            #   nix develop
            #   exec celery -A agl_monitor beat --loglevel=INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
            # '';
          };

          # Create service which runs before the django server
          # the service should 
          # - call a script which checks whether the ${service-dir} exists and if not, creates it (including the necessary parents)
          # - check if directory has owner and group set to ${config.services.agl-monitor.user} and ${config.services.agl-monitor.group}
          # - check if the directory has the correct permissions (0755)
          # Script is passed as "setup-script" and "script-name" in the configuration


          systemd.services.agl-monitor-pre = {
            description = "AGL Monitor Pre Service";
            after = [ "network.target" ];
            wantedBy = [ "multi-user.target" ];
            before = [ "agl-monitor.service" ]; 
            serviceConfig = {
              ExecStart = "${config.services.agl-monitor.setup-script}/bin/${config.services.agl-monitor.setup-script-name}";
              Restart = "always";
              RestartSec = "5";
              # WorkingDirectory = ./.; REQUIRED?!
              User = "root";  # Run as root to ensure directory creation and permissions are correct
              Group = "root";
              Environment = [];
            };
          };

          # Create the AGL Monitor Service
          systemd.services.agl-monitor = {
            description = "AGL Monitor Service";
            after = [ "network.target" "agl-monitor-pre.service" ];
            wantedBy = [ "multi-user.target" ];
            serviceConfig = {
              ExecStart = "${poetryApp}/bin/django-server";
              Restart = "always";
              RestartSec = "5";
              WorkingDirectory = ./.; # REQUIRED?!
              User = config.services.agl-monitor.user;
              Group = config.services.agl-monitor.group;
              Environment = [
                "PATH=/run/current-system/sw/bin/"
                # "PATH=${config.services.agl-home-django.working-directory}/.venv/bin:/run/current-system/sw/bin"
                "SERVICE_BASE_DIR=${config.services.agl-monitor.service-dir}"
                "DJANGO_SETTINGS_MODULE=${config.services.agl-monitor.django-settings-module}"
                "DJANGO_DEBUG=${toString config.services.agl-monitor.django-debug}"
                "CELERY_BROKER_URL=${config.services.agl-monitor.conf.CELERY_BROKER_URL}"
                "CELERY_RESULT_BACKEND=${config.services.agl-monitor.conf.CELERY_RESULT_BACKEND}"
                "CELERY_ACCEPT_CONTENT=${config.services.agl-monitor.conf.CELERY_ACCEPT_CONTENT}"
                "CELERY_TASK_SERIALIZER=${config.services.agl-monitor.conf.CELERY_TASK_SERIALIZER}"
                "CELERY_RESULT_SERIALIZER=${config.services.agl-monitor.conf.CELERY_RESULT_SERIALIZER}"
                "CELERY_TIMEZONE=${config.services.agl-monitor.conf.CELERY_TIMEZONE}"
                "CELERY_BEAT_SCHEDULER=${config.services.agl-monitor.conf.CELERY_BEAT_SCHEDULER}"
                "CELERY_SIGNAL_LOGFILE=${config.services.agl-monitor.conf.CELERY_SIGNAL_LOGFILE}"
              ];
            };
          };
        };

      };
    };

  };
}
