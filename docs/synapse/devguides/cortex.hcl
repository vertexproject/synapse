job "synapse-core01" {
  datacenters = ["us-east-1a"]

  # Use a constraint mechanism to force the scheduling of the job
  # on a host where the storage for the Cortex will be present.
  constraint {
    attribute = "${attr.unique.platform.aws.instance-id}"
    operator = "="
    value = "i-031c0dc19de2fb70c"
  }

  group "service" {
    task "svc" {
      driver = "docker"
      config {
        image = "vertexproject/synapse-cortex:v2.x.x"

        # This assumes that persistent data is stored at
        # /data/vertex on the host node
        volumes = [
          "/data/vertex/synapse_core01/:/vertex/storage",
        ]

        # Assign names to the telepath and https API ports
        # for later use.
        port_map {
          telepath = 27492
          https = 4433
        }
        force_pull = true
      }

      env {
        SYN_LOG_LEVEL = "DEBUG"
        SYN_CORTEX_AUTH_PASSWD = "secret"
        SYN_CORTEX_STORM_LOG = "true"
        SYN_CORTEX_STORM_LOG_LEVEL = "20"
      }

      # Setup services for later use with consul
      service {
        name = "synapse-core01"
        port = "telepath"
        tags = [
          "telepath"
        ]
      }

      service {
        name = "synapse-core01"
        port = "https"
        tags = [
          "https"
        ]
      }

      resources {
        cpu    = 1024
        memory = 1024

        network {
          mbits = 100

          port "telepath" {}
          port "https" {}
        }
      }
    }
  }
}
